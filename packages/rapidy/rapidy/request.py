from __future__ import annotations

import asyncio
import codecs
from collections.abc import Iterator, Mapping, MutableMapping
from dataclasses import dataclass
from http.cookies import SimpleCookie
from tempfile import SpooledTemporaryFile
from types import MappingProxyType
from typing import Any, cast, Final, NamedTuple, TYPE_CHECKING
from urllib.parse import parse_qsl

import python_multipart
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from python_multipart.multipart import parse_options_header
from rapidy_core.enums import HeaderName, HTTPRequestParamType

import rapidy as _rapidy
from rapidy.constants import DEFAULT_JSON_DECODER
from rapidy.exceptions import HTTPBadRequest, HTTPRequestEntityTooLarge
from rapidy.helpers import parse_mimetype
from rapidy.routing import reverse as _reverse
from rapidy.typedefs import ASGIScope, JSONDecoder, Receive, Send

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema
    from python_multipart.multipart import MultipartCallbacks

    from rapidy.application import Rapidy

__all__ = ('BaseRequest', 'FileField', 'MultipartLimits', 'Request', 'State')

_DEADLINE_HEADER: Final = 'x-rapidy-deadline-ms'
POST_METHODS: Final = frozenset({'POST', 'PUT', 'PATCH', 'DELETE', 'TRACE', 'PROPFIND', 'PROPPATCH', 'MKCOL'})


class _RequestDisconnectedError(ConnectionResetError):
    """Identify a peer disconnect reported by the request receive channel."""


@dataclass(frozen=True, slots=True)
class MultipartLimits:
    """Bound multipart resource use independently from ordinary request bodies."""

    max_body_size: int = 16 * 1024**2
    max_parts: int = 1000
    max_fields: int = 1000
    max_files: int = 100
    max_field_size: int = 1024**2
    max_file_size: int = 8 * 1024**2
    spool_threshold: int = 1024**2

    def __post_init__(self) -> None:
        for name in (
            'max_body_size',
            'max_parts',
            'max_fields',
            'max_files',
            'max_field_size',
            'max_file_size',
            'spool_threshold',
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                msg = f'{name} must be an integer'
                raise TypeError(msg)
            if value <= 0:
                msg = f'{name} must be greater than zero'
                raise ValueError(msg)


DEFAULT_MULTIPART_LIMITS: Final = MultipartLimits()


class FileField(NamedTuple):
    """One uploaded multipart file."""

    name: str
    filename: str
    file: SpooledTemporaryFile[bytes]
    content_type: str
    headers: CIMultiDictProxy[str]

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Represent an uploaded multipart file with OpenAPI's binary string schema."""
        return {'type': 'string', 'format': 'binary'}


class State(MutableMapping[str, Any]):
    """One string-keyed store with mapping and attribute access."""

    __slots__ = ('_data',)

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, '_data', data if data is not None else {})

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


class _MultipartCollector:
    """Collect low-level multipart callbacks into the public form representation."""

    __slots__ = (
        '_body',
        '_file',
        '_filename',
        '_header_field',
        '_header_value',
        '_headers',
        '_name',
        '_opened_files',
        '_out',
        '_part_size',
        '_parts',
        '_fields',
        '_files',
        '_limits',
    )

    def __init__(self, out: MultiDict[str | bytes | FileField], limits: MultipartLimits) -> None:
        self._out = out
        self._limits = limits
        self._opened_files: list[SpooledTemporaryFile[bytes]] = []
        self._parts = 0
        self._fields = 0
        self._files = 0
        self._part_size = 0
        self._headers: CIMultiDict[str] = CIMultiDict()
        self._header_field = bytearray()
        self._header_value = bytearray()
        self._body = bytearray()
        self._file: SpooledTemporaryFile[bytes] | None = None
        self._name: str | None = None
        self._filename: str | None = None

    @property
    def callbacks(self) -> MultipartCallbacks:
        """Return callbacks expected by ``python_multipart.MultipartParser``."""
        return {
            'on_part_begin': self.on_part_begin,
            'on_header_field': self.on_header_field,
            'on_header_value': self.on_header_value,
            'on_header_end': self.on_header_end,
            'on_headers_finished': self.on_headers_finished,
            'on_part_data': self.on_part_data,
            'on_part_end': self.on_part_end,
        }

    def on_part_begin(self) -> None:
        self._parts += 1
        _check_multipart_limit('part count', self._limits.max_parts, self._parts)
        self._headers = CIMultiDict()
        self._header_field.clear()
        self._header_value.clear()
        self._body.clear()
        self._file = None
        self._name = None
        self._filename = None
        self._part_size = 0

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._header_field.extend(data[start:end])

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._header_value.extend(data[start:end])

    def on_header_end(self) -> None:
        name = self._header_field.decode('latin-1')
        value = self._header_value.decode('latin-1')
        self._headers.add(name, value)
        self._header_field.clear()
        self._header_value.clear()

    def on_headers_finished(self) -> None:
        raw_disposition = self._headers.get('content-disposition')
        _, options = parse_options_header(raw_disposition)
        raw_name = options.get(b'name')
        if raw_name is None:
            msg = 'Multipart field missing name.'
            raise ValueError(msg)

        self._name = raw_name.decode('utf-8')
        raw_filename = options.get(b'filename')
        if raw_filename is not None:
            self._files += 1
            _check_multipart_limit('file count', self._limits.max_files, self._files)
            self._filename = raw_filename.decode('utf-8')
            uploaded_file = SpooledTemporaryFile(  # noqa: SIM115
                max_size=self._limits.spool_threshold,
                mode='w+b',
            )
            self._file = uploaded_file
            self._opened_files.append(uploaded_file)
        else:
            self._fields += 1
            _check_multipart_limit('field count', self._limits.max_fields, self._fields)

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        chunk = data[start:end]
        self._part_size += len(chunk)
        if self._file is not None:
            _check_multipart_limit('file size', self._limits.max_file_size, self._part_size)
            self._file.write(chunk)
        else:
            _check_multipart_limit('field size', self._limits.max_field_size, self._part_size)
            self._body.extend(chunk)

    def on_part_end(self) -> None:
        if self._name is None:
            msg = 'Multipart field missing name.'
            raise ValueError(msg)

        headers = CIMultiDictProxy(self._headers)
        if self._file is not None:
            self._file.seek(0)
            part_content_type = self._headers.get('content-type', 'application/octet-stream')
            self._out.add(
                self._name,
                FileField(self._name, self._filename or '', self._file, part_content_type, headers),
            )
            return

        field_content_type = self._headers.get('content-type')
        raw_value = bytes(self._body)
        if field_content_type is None or field_content_type.lower().startswith('text/'):
            charset = parse_mimetype(field_content_type or '').parameters.get('charset', 'utf-8')
            value: str | bytes = raw_value.decode(charset)
        else:
            value = raw_value
        self._out.add(self._name, value)

    def close_files(self) -> None:
        """Close all files if multipart parsing aborts."""
        for file_object in self._opened_files:
            file_object.close()


class Request:
    """Request view over an HTTP ASGI scope with one-shot body caching."""

    _asgi_send: Send
    _asgi_receive: Receive

    __slots__ = (
        '_asgi_send',
        '_asgi_receive',
        '_cache',
        '_body_file',
        '_cookies',
        '_deadline_remaining_ms',
        '_post',
        '_post_lock',
        '_query',
        '_read_bytes',
        '_read_lock',
        '_receive',
        'app',
        'headers',
        'method',
        'path',
        'path_params',
        'scope',
        'state',
    )

    def __init__(self, scope: ASGIScope, receive: Receive) -> None:
        self.scope = scope
        self._receive = receive
        self.method = str(scope['method']).upper()
        self.path = str(scope['path'])
        self.path_params = dict(cast('dict[str, str]', scope.get('path_params', {})))
        mutable_headers = CIMultiDict(
            (bytes(name).decode('latin-1'), bytes(value).decode('latin-1'))
            for name, value in cast('list[tuple[bytes, bytes]]', scope.get('headers', []))
        )
        self.headers: CIMultiDictProxy[str] = CIMultiDictProxy(mutable_headers)
        raw_state = cast('dict[str, Any]', scope.setdefault('state', {}))
        self.state = State(raw_state)
        self.app = cast('Rapidy', scope['app'])
        self._cache: dict[HTTPRequestParamType | str, Any] = {}
        self._read_bytes: bytes | None = None
        self._body_file: SpooledTemporaryFile[bytes] | None = None
        self._post: MultiDictProxy[str | bytes | FileField] | None = None
        self._read_lock = asyncio.Lock()
        self._post_lock = asyncio.Lock()
        self._query: MultiDictProxy[str] | None = None
        self._cookies: Mapping[str, str] | None = None
        self._deadline_remaining_ms = _parse_deadline_header(self.headers)

    @property
    def query(self) -> MultiDictProxy[str]:
        """Return decoded query parameters while retaining repeated keys."""
        if self._query is None:
            raw_query = cast('bytes', self.scope.get('query_string', b''))
            self._query = MultiDictProxy(
                MultiDict(parse_qsl(raw_query.decode('utf-8'), keep_blank_values=True))
            )
        return self._query

    @property
    def cookies(self) -> Mapping[str, str]:
        """Return a read-only cookie mapping."""
        if self._cookies is None:
            parsed = SimpleCookie()
            raw_cookie = self.headers.get(HeaderName.cookie)
            if raw_cookie is not None:
                parsed.load(raw_cookie)
            self._cookies = MappingProxyType({name: morsel.value for name, morsel in parsed.items()})
        return self._cookies

    @property
    def content_type(self) -> str:
        """Return the normalized media type, defaulting when the header is absent."""
        raw_content_type = self.headers.get(HeaderName.content_type)
        if raw_content_type is None:
            return 'application/octet-stream'
        return raw_content_type.partition(';')[0].strip().lower()

    @property
    def charset(self) -> str | None:
        """Return the declared content charset, if any."""
        raw_content_type = self.headers.get(HeaderName.content_type)
        if raw_content_type is None:
            return None
        return parse_mimetype(raw_content_type).parameters.get('charset')

    @property
    def body_exists(self) -> bool:
        """Estimate body presence from protocol-appropriate transport headers."""
        content_length = self.headers.get(HeaderName.content_length)
        http_version = str(self.scope.get('http_version', '1.1'))
        if http_version.startswith('1'):
            transfer_encoding = self.headers.get(HeaderName.transfer_encoding, '')
            return (content_length is not None and content_length != '0') or (
                'chunked' in transfer_encoding.lower()
            )
        return content_length is None or content_length != '0'

    @property
    def client_max_size(self) -> int:
        """Resolve the body limit from the currently bound application."""
        return self.app.client_max_size

    @property
    def multipart_limits(self) -> MultipartLimits:
        """Resolve multipart limits from the currently bound application."""
        return self.app.multipart_limits

    @property
    def identity(self) -> _rapidy.security.SecurityIdentity:
        """Return the current typed security identity, anonymous by default."""
        from rapidy.security import ANONYMOUS_IDENTITY  # noqa: PLC0415

        return cast(
            '_rapidy.security.SecurityIdentity',
            self.state.get('_rapidy_security_identity', ANONYMOUS_IDENTITY),
        )

    @property
    def user(self) -> Any:
        """Return the authenticated user object, or the stable anonymous user."""
        return self.identity.user

    @property
    def auth(self) -> _rapidy.security.AuthCredentials:
        """Return authenticated scheme and scope metadata without raw credential material."""
        return self.identity.auth

    @property
    def deadline_remaining_ms(self) -> int | None:
        """Return the validated deadline budget snapshot without enforcing it."""
        return self._deadline_remaining_ms

    def url_for(self, name: str, **path_params: object) -> _reverse.URLPath:
        """Build a named route URL including the deployment root path."""
        from rapidy.routing.reverse import URLPath  # noqa: PLC0415

        root_app = self.app._root_app or self.app  # noqa: SLF001
        path = root_app.url_for(name, **path_params)
        root_path = str(self.scope.get('root_path', '')).rstrip('/')
        return URLPath(f'{root_path}{path}')

    def static_url(self, name: str, path: str) -> _reverse.URLPath:
        """Build a URL for a named static file tree."""
        return self.url_for(name, path=path)

    async def read(self) -> bytes:
        """Read and cache the complete request body exactly once."""
        if self._read_bytes is not None:
            return self._read_bytes

        async with self._read_lock:
            if self._read_bytes is not None:
                return self._read_bytes

            if self._body_file is not None:
                self._body_file.seek(0, 2)
                body_size = self._body_file.tell()
                if self.client_max_size > 0 and body_size > self.client_max_size:
                    raise HTTPRequestEntityTooLarge(self.client_max_size, body_size)
                self._body_file.seek(0)
                self._read_bytes = self._body_file.read()
                self._body_file.close()
                self._body_file = None
                return self._read_bytes

            buffer = bytearray()
            while True:
                message = await self._receive()
                message_type = message.get('type')
                if message_type == 'http.disconnect':
                    msg = 'Connection lost while reading request body'
                    raise _RequestDisconnectedError(msg)
                if message_type != 'http.request':
                    continue

                buffer.extend(cast('bytes', message.get('body', b'')))
                if self.client_max_size > 0 and len(buffer) > self.client_max_size:
                    raise HTTPRequestEntityTooLarge(self.client_max_size, len(buffer))
                if not message.get('more_body', False):
                    break

            self._read_bytes = bytes(buffer)
            return self._read_bytes

    async def text(self) -> str:
        """Decode the cached body with the request charset or UTF-8."""
        charset = self.charset or 'utf-8'
        try:
            codecs.lookup(charset)
        except LookupError as exc:
            raise HTTPBadRequest(text='Unsupported request body charset.') from exc
        try:
            return (await self.read()).decode(charset)
        except UnicodeError as exc:
            raise HTTPBadRequest(text='Request body does not match the declared charset.') from exc

    async def json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Decode the cached body and pass it to a JSON loader."""
        return loads(await self.text())

    async def post(self) -> MultiDictProxy[str | bytes | FileField]:
        """Parse form data with independently bounded, streaming multipart handling."""
        if self._post is not None:
            return self._post

        async with self._post_lock:
            if self._post is not None:
                return self._post

            if self.method not in POST_METHODS or self.content_type not in (
                '',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
            ):
                self._post = MultiDictProxy(MultiDict())
                return self._post

            out: MultiDict[str | bytes | FileField] = MultiDict()
            if self.content_type == 'multipart/form-data':
                raw_content_type = self.headers.get(HeaderName.content_type, '')
                boundary = parse_mimetype(raw_content_type).parameters.get('boundary')
                if boundary is None:
                    msg = 'boundary missed for Content-Type: multipart/form-data'
                    raise ValueError(msg)
                await self._parse_multipart(boundary, out)
            else:
                data = await self.read()
                if data:
                    charset = self.charset or 'utf-8'
                    out.extend(
                        parse_qsl(
                            data.rstrip().decode(charset),
                            keep_blank_values=True,
                            encoding=charset,
                        )
                    )

            self._post = MultiDictProxy(out)
            return self._post

    async def _parse_multipart(
        self,
        boundary: str,
        out: MultiDict[str | bytes | FileField],
    ) -> None:
        limits = self.multipart_limits
        collector = _MultipartCollector(out, limits)
        parser = python_multipart.MultipartParser(
            boundary,
            collector.callbacks,
            max_size=limits.max_body_size,
        )
        try:
            async with self._read_lock:
                if self._read_bytes is not None:
                    _check_multipart_limit('body size', limits.max_body_size, len(self._read_bytes))
                    parser.write(self._read_bytes)
                elif self._body_file is not None:
                    self._body_file.seek(0, 2)
                    body_size = self._body_file.tell()
                    _check_multipart_limit('body size', limits.max_body_size, body_size)
                    self._body_file.seek(0)
                    while chunk := self._body_file.read(limits.spool_threshold):
                        parser.write(chunk)
                    self._body_file.seek(0)
                else:
                    await self._stream_multipart(parser, limits)
            parser.finalize()
        except BaseException:
            collector.close_files()
            raise

    async def _stream_multipart(
        self,
        parser: python_multipart.MultipartParser,
        limits: MultipartLimits,
    ) -> None:
        body_file = SpooledTemporaryFile[bytes](
            max_size=limits.spool_threshold,
            mode='w+b',
        )
        body_size = 0
        keep_open = False
        try:
            while True:
                message = await self._receive()
                message_type = message.get('type')
                if message_type == 'http.disconnect':
                    msg = 'Connection lost while reading request body'
                    raise _RequestDisconnectedError(msg)
                if message_type != 'http.request':
                    continue

                chunk = cast('bytes', message.get('body', b''))
                body_size += len(chunk)
                _check_multipart_limit('body size', limits.max_body_size, body_size)
                body_file.write(chunk)
                parser.write(chunk)
                if not message.get('more_body', False):
                    break

            body_file.seek(0)
            self._body_file = body_file
            keep_open = True
        finally:
            if not keep_open:
                body_file.close()


def _check_multipart_limit(kind: str, maximum: int, actual: int) -> None:
    if actual <= maximum:
        return
    text = f'Maximum multipart {kind} {maximum} exceeded, actual {kind} {actual}'
    raise HTTPRequestEntityTooLarge(maximum, actual, text=text)


def _parse_deadline_header(headers: CIMultiDictProxy[str]) -> int | None:
    raw_value = headers.get(_DEADLINE_HEADER)
    if raw_value is None:
        return None
    if not raw_value.isascii() or not raw_value.isdecimal():
        raise HTTPBadRequest(text='Invalid x-rapidy-deadline-ms header.')
    return int(raw_value)


BaseRequest = Request
