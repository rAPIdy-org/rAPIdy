from __future__ import annotations

import asyncio
import gzip
import zlib
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from functools import partial
from importlib import import_module
from typing import Any, cast, Literal, TYPE_CHECKING

from ._utils import add_response_hook, append_vary, response_headers
from rapidy.response import Response
from rapidy.responses.streaming import StreamResponse

if TYPE_CHECKING:
    from rapidy.request import Request
    from rapidy.typedefs import CallNext, HTTPResponse

__all__ = ('CompressionAlgorithm', 'CompressionMiddleware', 'GZipMiddleware', 'MissingBrotliDependencyError')

type CompressionAlgorithm = Literal['br', 'gzip']

_NO_BODY_STATUSES = frozenset({204, 304})
_MIN_INFORMATIONAL_STATUS = 100
_MIN_SUCCESS_STATUS = 200
_PARTIAL_CONTENT_STATUS = 206
_MAX_GZIP_LEVEL = 9
_MAX_BROTLI_QUALITY = 11
_NON_COMPRESSIBLE_PREFIXES = ('audio/', 'image/', 'video/')
_NON_COMPRESSIBLE_TYPES = frozenset(
    {
        'application/gzip',
        'application/octet-stream',
        'application/pdf',
        'application/zip',
        'application/x-7z-compressed',
        'application/x-brotli',
        'application/x-rar-compressed',
        'text/event-stream',
    }
)


class MissingBrotliDependencyError(ImportError):
    """Raised when Brotli is configured without the ``rapidy[brotli]`` extra."""


class CompressionMiddleware:
    """Negotiate and apply real gzip or optional Brotli response compression."""

    __slots__ = ('_algorithms', '_brotli_quality', '_gzip_level', '_minimum_size')

    def __init__(
        self,
        *,
        algorithms: Iterable[CompressionAlgorithm] = ('gzip',),
        minimum_size: int = 500,
        gzip_level: int = 6,
        brotli_quality: int = 4,
    ) -> None:
        normalized = tuple(dict.fromkeys(algorithms))
        if not normalized or any(algorithm not in ('br', 'gzip') for algorithm in normalized):
            msg = "algorithms must contain 'gzip' and/or 'br'"
            raise ValueError(msg)
        if minimum_size < 0:
            msg = 'minimum_size must be greater than or equal to zero'
            raise ValueError(msg)
        if not 0 <= gzip_level <= _MAX_GZIP_LEVEL:
            msg = 'gzip_level must be between 0 and 9'
            raise ValueError(msg)
        if not 0 <= brotli_quality <= _MAX_BROTLI_QUALITY:
            msg = 'brotli_quality must be between 0 and 11'
            raise ValueError(msg)
        if 'br' in normalized:
            _load_brotli()
        self._algorithms = normalized
        self._minimum_size = minimum_size
        self._gzip_level = gzip_level
        self._brotli_quality = brotli_quality

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Register transport-safe compression before downstream dispatch."""
        if request.method == 'HEAD' or 'range' in request.headers:
            return await call_next(request)
        selected = _select_algorithm(','.join(request.headers.getall('accept-encoding', [])), self._algorithms)
        add_response_hook(request, lambda response: self._compress_response(response, selected))
        return await call_next(request)

    async def _compress_response(
        self,
        response: HTTPResponse,
        algorithm: CompressionAlgorithm | None,
    ) -> None:
        headers = response_headers(response)
        content_type = _response_content_type(response, headers)
        if not _may_compress(response.status, content_type, headers):
            return
        if isinstance(response, Response):
            body = response.body or b''
            if len(body) < self._minimum_size:
                return
            append_vary(headers, 'Accept-Encoding')
            if algorithm is None:
                return
            response.body = await self._compress_buffered(response, body, algorithm)
            _set_compression_headers(headers, algorithm, len(response.body or b''))
            return
        if isinstance(response, StreamResponse) and response._body is not None:  # noqa: SLF001
            append_vary(headers, 'Accept-Encoding')
            if algorithm is None:
                return
            response._body = self._compress_stream(response._body, algorithm)  # noqa: SLF001
            _set_compression_headers(headers, algorithm, None)

    async def _compress_buffered(
        self,
        response: Response,
        body: bytes,
        algorithm: CompressionAlgorithm,
    ) -> bytes:
        executor = response._zlib_executor  # noqa: SLF001
        executor_size = response._zlib_executor_size  # noqa: SLF001
        compress = partial(
            _compress_bytes,
            body,
            algorithm=algorithm,
            gzip_level=self._gzip_level,
            brotli_quality=self._brotli_quality,
        )
        if executor is not None and (executor_size is None or len(body) >= executor_size):
            return await asyncio.get_running_loop().run_in_executor(executor, compress)
        return compress()

    async def _compress_stream(
        self,
        body: AsyncIterable[bytes | str],
        algorithm: CompressionAlgorithm,
    ) -> AsyncIterator[bytes]:
        compressor = _StreamingCompressor(
            algorithm,
            gzip_level=self._gzip_level,
            brotli_quality=self._brotli_quality,
        )
        try:
            async for chunk in body:
                data = chunk.encode() if isinstance(chunk, str) else chunk
                compressed = compressor.process(data)
                if compressed:
                    yield compressed
            final = compressor.finish()
            if final:
                yield final
        finally:
            close = getattr(body, 'aclose', None)
            if close is not None:
                await close()


class GZipMiddleware(CompressionMiddleware):
    """Convenience gzip-only compression middleware."""

    __slots__ = ()

    def __init__(self, *, minimum_size: int = 500, compress_level: int = 6) -> None:
        super().__init__(algorithms=('gzip',), minimum_size=minimum_size, gzip_level=compress_level)


class _StreamingCompressor:
    __slots__ = ('_algorithm', '_compressor')

    def __init__(
        self,
        algorithm: CompressionAlgorithm,
        *,
        gzip_level: int,
        brotli_quality: int,
    ) -> None:
        self._algorithm = algorithm
        if algorithm == 'gzip':
            self._compressor: Any = zlib.compressobj(gzip_level, zlib.DEFLATED, wbits=31)
        else:
            self._compressor = _load_brotli().Compressor(quality=brotli_quality)

    def process(self, data: bytes) -> bytes:
        if self._algorithm == 'gzip':
            return cast('bytes', self._compressor.compress(data) + self._compressor.flush(zlib.Z_SYNC_FLUSH))
        return cast('bytes', self._compressor.process(data) + self._compressor.flush())

    def finish(self) -> bytes:
        if self._algorithm == 'gzip':
            return cast('bytes', self._compressor.flush(zlib.Z_FINISH))
        return cast('bytes', self._compressor.finish())


def _compress_bytes(
    body: bytes,
    *,
    algorithm: CompressionAlgorithm,
    gzip_level: int,
    brotli_quality: int,
) -> bytes:
    if algorithm == 'gzip':
        return gzip.compress(body, compresslevel=gzip_level, mtime=0)
    return cast('bytes', _load_brotli().compress(body, quality=brotli_quality))


def _load_brotli() -> Any:
    try:
        return import_module('brotli')
    except ImportError as exc:
        msg = "Brotli compression requires the optional 'rapidy[brotli]' extra"
        raise MissingBrotliDependencyError(msg) from exc


def _select_algorithm(
    accept_encoding: str | None,
    algorithms: tuple[CompressionAlgorithm, ...],
) -> CompressionAlgorithm | None:
    if accept_encoding is None or not accept_encoding.strip():
        return None
    qualities: dict[str, float] = {}
    for item in accept_encoding.split(','):
        token, *parameters = item.strip().lower().split(';')
        quality = 1.0
        for parameter in parameters:
            name, separator, value = parameter.strip().partition('=')
            if name == 'q' and separator:
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if not 0 <= quality <= 1:
            quality = 0.0
        qualities[token] = quality
    selected: CompressionAlgorithm | None = None
    selected_quality = 0.0
    wildcard_quality = qualities.get('*', 0.0)
    for algorithm in algorithms:
        quality = qualities.get(algorithm, wildcard_quality)
        if algorithm == 'gzip':
            quality = max(quality, qualities.get('x-gzip', 0.0))
        if quality > selected_quality:
            selected = algorithm
            selected_quality = quality
    return selected


def _may_compress(status: int, content_type: str, headers: Any) -> bool:
    if (
        _MIN_INFORMATIONAL_STATUS <= status < _MIN_SUCCESS_STATUS
        or status in _NO_BODY_STATUSES
        or status == _PARTIAL_CONTENT_STATUS
    ):
        return False
    if 'content-encoding' in headers or 'content-range' in headers:
        return False
    if 'no-transform' in ','.join(headers.getall('cache-control', [])).lower():
        return False
    return _is_compressible_content_type(content_type)


def _response_content_type(response: HTTPResponse, headers: Any) -> str:
    return str(headers.get('content-type', response.content_type)).partition(';')[0].strip().lower()


def _is_compressible_content_type(content_type: str) -> bool:
    if content_type == 'image/svg+xml':
        return True
    if content_type in _NON_COMPRESSIBLE_TYPES or content_type.startswith(_NON_COMPRESSIBLE_PREFIXES):
        return False
    return content_type.startswith(('text/', 'application/'))


def _set_compression_headers(headers: Any, algorithm: CompressionAlgorithm, length: int | None) -> None:
    headers['content-encoding'] = algorithm
    headers.popall('content-length', None)
    if length is not None:
        headers['content-length'] = str(length)
    headers.popall('content-md5', None)
    headers.popall('content-digest', None)
    headers.popall('digest', None)
    headers.popall('repr-digest', None)
    etag = headers.get('etag')
    if etag is not None and not etag.startswith('W/'):
        headers['etag'] = f'W/{etag}'
