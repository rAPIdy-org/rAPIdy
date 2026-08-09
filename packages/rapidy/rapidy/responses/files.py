from __future__ import annotations

import asyncio
import mimetypes
import os
import re
import stat as stat_module
from collections.abc import AsyncIterator, Callable
from email.utils import formatdate, parsedate_to_datetime
from os import PathLike
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from rapidy import request as _request
from rapidy.background import Background, BackgroundCallable
from rapidy.exceptions import HTTPNotFound, HTTPRequestRangeNotSatisfiable
from rapidy.responses.streaming import StreamResponse
from rapidy.typedefs import LooseHeaders, Receive, Send

__all__ = ('FileResponse',)

HTTP_OK = 200
_BYTE_RANGE_PATTERN = re.compile(r'^[0-9]*-[0-9]*$')


class FileResponse(StreamResponse):
    """Stream one regular file with validators, byte ranges, and ASGI send extensions."""

    __slots__ = (
        '_chunk_size',
        '_count',
        '_extensions',
        '_file_object',
        '_file_path',
        '_is_head',
        '_offset',
        '_opener',
        '_use_pathsend',
        '_use_zerocopysend',
    )

    def __init__(
        self,
        path: str | PathLike[str],
        *,
        headers: LooseHeaders | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        content_disposition_type: str = 'attachment',
        chunk_size: int = 64 * 1024,
        background: Background | BackgroundCallable | None = None,
        _opener: Callable[[], BinaryIO] | None = None,
    ) -> None:
        if chunk_size < 1:
            msg = 'chunk_size must be greater than zero'
            raise ValueError(msg)
        if content_disposition_type not in {'attachment', 'inline'}:
            msg = 'content_disposition_type must be `attachment` or `inline`'
            raise ValueError(msg)
        self._file_path = Path(path).expanduser().absolute()
        self._chunk_size = chunk_size
        self._offset = 0
        self._count = 0
        self._extensions: dict[str, object] = {}
        self._file_object: BinaryIO | None = None
        self._is_head = False
        self._opener = _opener
        self._use_pathsend = False
        self._use_zerocopysend = False
        resolved_media_type = media_type or mimetypes.guess_type(str(self._file_path))[0] or 'application/octet-stream'
        super().__init__(
            status=200,
            headers=headers,
            content_type=resolved_media_type,
            background=background,
        )
        if filename is not None:
            self.headers['Content-Disposition'] = _content_disposition(filename, content_disposition_type)

    @property
    def path(self) -> Path:
        """Return the absolute configured file path."""
        return self._file_path

    async def prepare(self, request: _request.Request) -> None:
        """Resolve file metadata and request preconditions before starting the response."""
        if self._started:
            return
        file_stat = await self._open_and_stat()
        try:
            file_size = file_stat.st_size
            etag = f'"{file_stat.st_mtime_ns:x}-{file_size:x}"'
            self.headers['Accept-Ranges'] = 'bytes'
            self.headers['ETag'] = etag
            self.headers['Last-Modified'] = formatdate(file_stat.st_mtime, usegmt=True)
            self._is_head = request.method == 'HEAD'
            self._extensions = dict(request.scope.get('extensions', {}))

            is_retrieval = request.method in {'GET', 'HEAD'}
            if is_retrieval and _is_not_modified(request, etag, file_stat.st_mtime):
                self.status = 304
                self.headers.popall('content-length', None)
                self._body = None
                await self._close_file_object()
                await super().prepare(request)
                return

            offset, count, content_range = _requested_range(
                request,
                etag=etag,
                modified_at=file_stat.st_mtime,
                file_size=file_size,
            )
            if content_range is not None:
                self.status = 206
                self.headers['Content-Range'] = content_range
            self._offset = offset
            self._count = count
            self.headers['Content-Length'] = str(count)
            self._use_pathsend = (
                not self._is_head
                and self.status == HTTP_OK
                and self._opener is None
                and 'http.response.pathsend' in self._extensions
            )
            self._use_zerocopysend = (
                not self._is_head
                and not self._use_pathsend
                and 'http.response.zerocopysend' in self._extensions
            )
            self._body = (
                None
                if self._is_head
                else _file_chunks(
                    self._file_path,
                    offset,
                    count,
                    self._chunk_size,
                    file_object=self._file_object,
                )
            )
            if self._is_head:
                await self._close_file_object()
            await super().prepare(request)
        except BaseException:
            await self._close_file_object()
            raise

    async def _open_and_stat(self) -> os.stat_result:
        try:
            if self._opener is None:
                file_stat = await asyncio.to_thread(self._file_path.stat)
            else:
                self._file_object = await asyncio.to_thread(self._opener)
                file_stat = await asyncio.to_thread(os.fstat, self._file_object.fileno())
        except OSError as exc:
            await self._close_file_object()
            raise HTTPNotFound from exc
        if not stat_module.S_ISREG(file_stat.st_mode):
            await self._close_file_object()
            raise HTTPNotFound
        return file_stat

    async def _send_stream(
        self,
        send: Send,
        receive: Receive,
        *,
        server_info: str | None = None,
    ) -> None:
        try:
            if self._sent:
                return
            if self._use_pathsend:
                await self._guarded_send(
                    send,
                    {'type': 'http.response.pathsend', 'path': str(self._file_path)},
                )
                self._eof_sent = True
                self._sent = True
                return
            if self._use_zerocopysend:
                file_object = self._file_object
                if file_object is None:
                    file_object = await asyncio.to_thread(self._file_path.open, 'rb')
                    self._file_object = file_object
                await self._guarded_send(
                    send,
                    {
                        'type': 'http.response.zerocopysend',
                        'file': file_object,
                        'offset': self._offset,
                        'count': self._count,
                        'more_body': False,
                    },
                )
                self._eof_sent = True
                self._sent = True
                return
            await super()._send_stream(send, receive, server_info=server_info)
        finally:
            await self._close_file_object()

    async def _close_file_object(self) -> None:
        file_object = self._file_object
        self._file_object = None
        if file_object is not None and not file_object.closed:
            await asyncio.to_thread(file_object.close)

    def _preserve_content_length(self) -> bool:
        return True


async def _file_chunks(
    path: Path,
    offset: int,
    count: int,
    chunk_size: int,
    *,
    file_object: BinaryIO | None = None,
) -> AsyncIterator[bytes]:
    if file_object is None:
        file_object = await asyncio.to_thread(path.open, 'rb')
    remaining = count
    try:
        if offset:
            await asyncio.to_thread(file_object.seek, offset)
        while remaining:
            chunk = await asyncio.to_thread(file_object.read, min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        await asyncio.to_thread(file_object.close)


def _requested_range(
    request: _request.Request,
    *,
    etag: str,
    modified_at: float,
    file_size: int,
) -> tuple[int, int, str | None]:
    range_header = _single_header(request, 'range')
    if (
        request.method not in {'GET', 'HEAD'}
        or range_header is None
        or not _if_range_matches(request, etag, modified_at)
        or range_header.partition('=')[0].strip().lower() != 'bytes'
    ):
        return 0, file_size, None
    try:
        parsed_range = _parse_range(range_header, file_size)
    except (TypeError, ValueError) as exc:
        raise HTTPRequestRangeNotSatisfiable(
            headers={'Content-Range': f'bytes */{file_size}', 'Accept-Ranges': 'bytes'}
        ) from exc
    if parsed_range is None:
        return 0, file_size, None
    offset, count = parsed_range
    return offset, count, f'bytes {offset}-{offset + count - 1}/{file_size}'


def _single_header(request: _request.Request, name: str) -> str | None:
    values = request.headers.getall(name, [])
    if not values:
        return None
    if len(values) != 1:
        return ','.join(values)
    return values[0]


def _is_not_modified(request: _request.Request, etag: str, modified_at: float) -> bool:
    if_none_match = _single_header(request, 'if-none-match')
    if if_none_match is not None:
        return _etag_matches(if_none_match, etag, weak=True)
    if_modified_since = _single_header(request, 'if-modified-since')
    if if_modified_since is None:
        return False
    timestamp = _http_date_timestamp(if_modified_since)
    return timestamp is not None and int(modified_at) <= int(timestamp)


def _if_range_matches(request: _request.Request, etag: str, modified_at: float) -> bool:
    if_range = _single_header(request, 'if-range')
    if if_range is None:
        return True
    if_range = if_range.strip()
    if if_range.startswith('W/'):
        return False
    if if_range.startswith('"'):
        return if_range.strip() == etag
    timestamp = _http_date_timestamp(if_range)
    return timestamp is not None and int(modified_at) <= int(timestamp)


def _etag_matches(field: str, etag: str, *, weak: bool) -> bool:
    if field.strip() == '*':
        return True
    normalized = etag.removeprefix('W/') if weak else etag
    for raw_candidate in field.split(','):
        candidate = raw_candidate.strip()
        if weak:
            candidate = candidate.removeprefix('W/')
        if candidate == normalized:
            return True
    return False


def _http_date_timestamp(value: str) -> float | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.timestamp()


def _parse_range(value: str, size: int) -> tuple[int, int] | None:
    unit, separator, raw_range = value.partition('=')
    if not separator or unit.lower() != 'bytes':
        msg = 'invalid byte range unit'
        raise ValueError(msg)
    if ',' in raw_range:
        return None
    if _BYTE_RANGE_PATTERN.fullmatch(raw_range) is None:
        msg = 'invalid byte range grammar'
        raise ValueError(msg)
    start_text, dash, end_text = raw_range.partition('-')
    if not dash or (not start_text and not end_text) or size == 0:
        msg = 'invalid byte range'
        raise ValueError(msg)
    if not start_text:
        suffix = int(end_text)
        if suffix <= 0:
            msg = 'invalid suffix byte range'
            raise ValueError(msg)
        count = min(suffix, size)
        return size - count, count
    start = int(start_text)
    if start < 0 or start >= size:
        msg = 'byte range starts beyond the file'
        raise ValueError(msg)
    end = size - 1 if not end_text else min(int(end_text), size - 1)
    if end < start:
        msg = 'byte range ends before it starts'
        raise ValueError(msg)
    return start, end - start + 1


def _content_disposition(filename: str, disposition_type: str) -> str:
    if any(character in filename for character in ('\x00', '\r', '\n')):
        msg = 'filename must not contain control characters'
        raise ValueError(msg)
    quoted = quote(filename, safe='')
    try:
        latin_filename = filename.encode('latin-1').decode('latin-1')
    except UnicodeEncodeError:
        return f"{disposition_type}; filename*=UTF-8''{quoted}"
    escaped = latin_filename.replace('\\', '\\\\').replace('"', '\\"')
    return f'{disposition_type}; filename="{escaped}"'
