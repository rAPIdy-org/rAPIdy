from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from concurrent.futures import Executor
from decimal import Decimal
from enum import Enum
from http.cookies import SimpleCookie
from typing import Any, Counter, DefaultDict

from multidict import CIMultiDict
from pydantic import BaseModel
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.encoders import CustomEncoder, Exclude, Include, jsonify
from rapidy_core.enums import Charset, ContentType
from rapidy_core.typedefs import JSONEncoder  # noqa: TC002 - runtime annotations

from rapidy._base_exceptions import RapidyException
from rapidy.background import Background, BackgroundCallable, BackgroundRunner
from rapidy.helpers import parse_mimetype
from rapidy.typedefs import LooseHeaders, Send

__all__ = ('StreamResponse', 'Response')

DEFAULT_JSON_TYPES: tuple[type[Any], ...] = (
    BaseModel,
    dict,
    list,
    tuple,
    set,
    frozenset,
    DefaultDict,
    Counter,
)
DEFAULT_TEXT_PLAIN_TYPES: tuple[type[Any], ...] = (str, Enum, int, float, Decimal, bool)
MIN_INFORMATIONAL_STATUS = 100
MIN_SUCCESS_STATUS = 200
NO_BODY_STATUSES = {204, 304}


class ResponseDuplicateBodyError(RapidyException):
    """Raised when both compatibility body inputs are provided."""

    message = '`body` and `text` are not allowed together'


class ResponseEncodeError(RapidyException):
    """Raised when a response value cannot be serialized."""

    message = 'Encoding errors: \n {errors}'


def _as_header_text(value: str | bytes) -> str:
    return value.decode('latin-1') if isinstance(value, bytes) else value


def _make_headers(headers: LooseHeaders | None) -> CIMultiDict[str]:
    if headers is None:
        return CIMultiDict()
    if isinstance(headers, Mapping):
        return CIMultiDict(headers)
    return CIMultiDict((_as_header_text(key), _as_header_text(value)) for key, value in headers)


def _enum_value(value: str | Enum | None) -> str | None:
    return str(value.value) if isinstance(value, Enum) else value


class Response:
    """Mutable response value object with rAPIdy-compatible serialization."""

    __slots__ = (
        '_body',
        '_background',
        '_by_alias',
        '_charset',
        '_content_type',
        '_cookies',
        '_custom_encoder',
        '_exclude_defaults',
        '_exclude_fields',
        '_exclude_none',
        '_exclude_unset',
        '_headers',
        '_include_fields',
        '_json_encoder',
        '_reason',
        '_status',
        '_zlib_executor',
        '_zlib_executor_size',
    )

    def __init__(
        self,
        body: Any | None = None,
        *,
        status: int = 200,
        headers: LooseHeaders | None = None,
        content_type: str | ContentType | None = None,
        charset: str | Charset | None = None,
        zlib_executor: Executor | None = None,
        zlib_executor_size: int | None = None,
        include: Include | None = None,
        exclude: Exclude | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        custom_encoder: CustomEncoder | None = None,
        json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
        text: Any | None = None,
        reason: str | None = None,
        background: Background | BackgroundCallable | None = None,
    ) -> None:
        """Create a response; zlib options tune an active compression middleware."""
        from rapidy.background import normalize_background  # noqa: PLC0415

        self._json_encoder = json_encoder
        self._include_fields = include
        self._exclude_fields = exclude
        self._by_alias = by_alias
        self._exclude_unset = exclude_unset
        self._exclude_defaults = exclude_defaults
        self._exclude_none = exclude_none
        self._custom_encoder = custom_encoder

        self._status = int(status)
        self._reason = reason
        self._headers = _make_headers(headers)
        self._cookies = SimpleCookie()
        self._body: bytes | None = None
        self._content_type = _enum_value(content_type)
        self._charset = _enum_value(charset)
        self._zlib_executor = zlib_executor
        self._zlib_executor_size = zlib_executor_size
        self._background = normalize_background(background)

        body_exists = body is not None
        text_exists = text is not None
        if body_exists and text_exists:
            raise ResponseDuplicateBodyError
        if body_exists:
            self.body = body
        if text_exists:
            self.text = text

    @property
    def status(self) -> int:
        """Return the HTTP status code."""
        return self._status

    @status.setter
    def status(self, value: int) -> None:
        self._status = int(value)

    @property
    def background(self) -> BackgroundRunner | None:
        """Return the post-response task attached to this response."""
        return self._background

    @background.setter
    def background(self, value: Background | BackgroundCallable | None) -> None:
        from rapidy.background import normalize_background  # noqa: PLC0415

        self._background = normalize_background(value)

    def set_status(self, status: int) -> None:
        """Set the HTTP status code using the rAPIdy 1.x compatibility API."""
        self.status = status

    @property
    def reason(self) -> str | None:
        """Return the optional HTTP reason phrase."""
        return self._reason

    @reason.setter
    def reason(self, value: str | None) -> None:
        self._reason = value

    @property
    def headers(self) -> CIMultiDict[str]:
        """Return the live case-insensitive response headers."""
        return self._headers

    @headers.setter
    def headers(self, value: LooseHeaders) -> None:
        self._headers = _make_headers(value)

    @property
    def content_type(self) -> str:
        """Return the configured media type or the binary default."""
        return self._content_type if self._content_type is not None else ContentType.stream.value

    @content_type.setter
    def content_type(self, value: str | ContentType | None) -> None:
        self._content_type = _enum_value(value)

    @property
    def charset(self) -> str:
        """Return the configured charset or UTF-8."""
        return self._charset if self._charset is not None else Charset.utf8.value

    @charset.setter
    def charset(self, value: str | Charset | None) -> None:
        self._charset = _enum_value(value)

    @property
    def body(self) -> bytes | None:
        """Return the encoded body bytes."""
        return self._body

    @body.setter
    def body(self, body: Any | None) -> None:
        if body is None or isinstance(body, bytes):
            self._body = body
            return
        self._set_body(body)

    def _set_pre_serialized_body(self, body: Any) -> None:
        """Encode a declared-contract value without applying field filters twice."""
        field_filters = self._include_fields, self._exclude_fields
        self._include_fields = None
        self._exclude_fields = None
        try:
            self.body = body
        finally:
            self._include_fields, self._exclude_fields = field_filters

    @property
    def text(self) -> str | None:
        """Decode the body with the effective charset."""
        if self._body is None:
            return None
        return self._body.decode(self.charset)

    @text.setter
    def text(self, text: Any | None) -> None:
        if text is None or isinstance(text, str):
            self._set_text(text)
            return
        self._set_body(text)

    def _set_body(self, body: Any | None) -> None:
        current_ctype = self.content_type if self.content_type != ContentType.stream.value else None
        if current_ctype is None:
            current_ctype = self._get_and_set_ctype_by_data(body).value

        ctype_obj = parse_mimetype(current_ctype)
        if ctype_obj.type == 'application' and ctype_obj.subtype == 'json':
            self._process_json_body(body)
        elif ctype_obj.type == 'text':
            self._process_text_body(body)
        else:
            self._process_bytes_body(body)

    def _set_text(self, text: str | None) -> None:
        if text is None:
            self._body = None
            return
        if self._content_type is None:
            self._content_type = ContentType.text_plain.value
        self._body = text.encode(self.charset)

    def _process_json_body(self, body: Any) -> None:
        self._set_text(self._simplify_body(body, charset=self.charset))

    def _process_text_body(self, body: Any) -> None:
        if not isinstance(body, str):
            body = self._simplify_body(body, charset=self.charset, dumps=False)
            if not isinstance(body, str):
                body = self._json_encoder(body)
        self._set_text(body)

    def _process_bytes_body(self, body: Any) -> None:
        if not isinstance(body, str):
            body = self._simplify_body(body, charset=self.charset)
        self.body = body.encode(self.charset)

    def _simplify_body(self, obj: Any, *, charset: str, dumps: bool = True) -> str:
        try:
            return jsonify(
                obj,
                include=self._include_fields,
                exclude=self._exclude_fields,
                by_alias=self._by_alias,
                exclude_unset=self._exclude_unset,
                exclude_defaults=self._exclude_defaults,
                exclude_none=self._exclude_none,
                custom_encoder=self._custom_encoder,
                charset=charset,
                dumps_encoder=self._json_encoder,
                dumps=dumps,
            )
        except Exception as encode_exc:
            raise ResponseEncodeError(errors=str(encode_exc)) from encode_exc

    def _get_and_set_ctype_by_data(self, data: Any) -> ContentType:
        if isinstance(data, DEFAULT_JSON_TYPES) or dataclasses.is_dataclass(data):
            self.content_type = ContentType.json.value
            return ContentType.json
        if isinstance(data, DEFAULT_TEXT_PLAIN_TYPES):
            return ContentType.text_plain
        return ContentType.stream

    def set_cookie(
        self,
        name: str,
        value: str,
        *,
        expires: str | None = None,
        domain: str | None = None,
        max_age: int | None = None,
        path: str = '/',
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = 'lax',
    ) -> None:
        """Set one response cookie."""
        if samesite is not None and samesite.lower() not in {'lax', 'strict', 'none'}:
            msg = 'samesite must be `lax`, `strict`, `none`, or None'
            raise ValueError(msg)
        self._cookies[name] = value
        morsel = self._cookies[name]
        if expires is not None:
            morsel['expires'] = expires
        if domain is not None:
            morsel['domain'] = domain
        if max_age is not None:
            morsel['max-age'] = str(max_age)
        if path is not None:
            morsel['path'] = path
        if secure:
            morsel['secure'] = secure
        if httponly:
            morsel['httponly'] = httponly
        if samesite is not None:
            morsel['samesite'] = samesite.capitalize()

    def del_cookie(self, name: str, *, domain: str | None = None, path: str = '/') -> None:
        """Expire one response cookie immediately."""
        self.set_cookie(
            name,
            '',
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            domain=domain,
            max_age=0,
            path=path,
        )

    async def _send(self, send: Send, *, server_info: str | None = None) -> None:
        headers = CIMultiDict(self._headers)
        body_forbidden = (
            MIN_INFORMATIONAL_STATUS <= self._status < MIN_SUCCESS_STATUS or self._status in NO_BODY_STATUSES
        )

        if 'content-type' not in headers and (self._content_type is not None or self._body is not None):
            content_type = self.content_type
            parsed_content_type = parse_mimetype(content_type)
            needs_charset = (
                parsed_content_type.type == 'text'
                or (parsed_content_type.type == 'application' and parsed_content_type.subtype == 'json')
                or self._charset is not None
            )
            if needs_charset and 'charset' not in parsed_content_type.parameters:
                content_type = f'{content_type}; charset={self.charset}'
            headers['content-type'] = content_type

        if body_forbidden:
            headers.popall('content-length', None)
        elif 'content-length' not in headers:
            headers['content-length'] = str(len(self._body or b''))

        for morsel in self._cookies.values():
            headers.add('set-cookie', morsel.OutputString())
        if server_info is not None and 'server' not in headers:
            headers['server'] = server_info

        encoded_headers = [(key.encode('latin-1'), value.encode('latin-1')) for key, value in headers.items()]
        await send({'type': 'http.response.start', 'status': self._status, 'headers': encoded_headers})
        await send(
            {
                'type': 'http.response.body',
                'body': b'' if body_forbidden else self._body or b'',
                'more_body': False,
            }
        )


# Imported after Response is defined because rapidy.responses also exports FileResponse,
# whose exception imports refer back to this module during package initialization.
from rapidy.responses.streaming import StreamResponse  # noqa: E402
