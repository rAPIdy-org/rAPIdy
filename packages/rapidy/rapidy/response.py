from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Executor
from typing import Any, TYPE_CHECKING

from multidict import CIMultiDict
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType

from rapidy.exceptions import ResponseDuplicateBodyError
from rapidy.typedefs import LooseHeaders, Send

if TYPE_CHECKING:
    from rapidy_core.encoders import CustomEncoder, Exclude, Include
    from rapidy_core.typedefs import JSONEncoder

__all__ = ('Response',)


def _as_header_text(value: str | bytes) -> str:
    return value.decode('latin-1') if isinstance(value, bytes) else value


class Response:
    """Minimal ASGI response; full serialization is completed in milestone 10."""

    __slots__ = (
        '_body',
        '_by_alias',
        '_custom_encoder',
        '_exclude',
        '_exclude_defaults',
        '_exclude_none',
        '_exclude_unset',
        '_include',
        '_json_encoder',
        '_zlib_executor',
        '_zlib_executor_size',
        'charset',
        'content_type',
        'headers',
        'reason',
        'status',
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
    ) -> None:
        if body is not None and text is not None:
            raise ResponseDuplicateBodyError

        self.status = status
        if headers is None:
            self.headers: CIMultiDict[str] = CIMultiDict()
        elif isinstance(headers, Mapping):
            self.headers = CIMultiDict(headers)
        else:
            self.headers = CIMultiDict((_as_header_text(k), _as_header_text(v)) for k, v in headers)

        self.content_type = str(content_type) if content_type is not None else None
        self.charset = str(charset) if charset is not None else None
        self.reason = reason
        self._zlib_executor = zlib_executor
        self._zlib_executor_size = zlib_executor_size
        self._include = include
        self._exclude = exclude
        self._by_alias = by_alias
        self._exclude_unset = exclude_unset
        self._exclude_defaults = exclude_defaults
        self._exclude_none = exclude_none
        self._custom_encoder = custom_encoder
        self._json_encoder = json_encoder
        self._body = b''
        self.body = text if text is not None else body

    @property
    def body(self) -> bytes:
        """Return the encoded body bytes."""
        return self._body

    @body.setter
    def body(self, value: Any | None) -> None:
        if value is None:
            self._body = b''
            return
        if isinstance(value, bytes):
            self._body = value
            if self.content_type is None:
                self.content_type = ContentType.stream.value
            return
        if isinstance(value, str):
            encoding = self.charset or Charset.utf8.value
            self.charset = encoding
            self._body = value.encode(encoding)
            if self.content_type is None:
                self.content_type = ContentType.text_plain.value
            return
        msg = 'Milestone 02 responses accept only None, bytes, or str bodies'
        raise NotImplementedError(msg)

    @property
    def text(self) -> str | None:
        """Decode the body with the configured charset."""
        if not self._body:
            return None
        return self._body.decode(self.charset or Charset.utf8.value)

    @text.setter
    def text(self, value: Any | None) -> None:
        self.body = value

    async def _send(self, send: Send, *, server_info: str | None = None) -> None:
        headers = CIMultiDict(self.headers)
        if self.content_type is not None and 'content-type' not in headers:
            content_type = self.content_type
            if self.charset is not None:
                content_type = f'{content_type}; charset={self.charset}'
            headers['content-type'] = content_type
        if 'content-length' not in headers:
            headers['content-length'] = str(len(self._body))
        if server_info is not None and 'server' not in headers:
            headers['server'] = server_info

        encoded_headers = [(key.encode('latin-1'), value.encode('latin-1')) for key, value in headers.items()]
        await send({'type': 'http.response.start', 'status': self.status, 'headers': encoded_headers})
        await send({'type': 'http.response.body', 'body': self._body, 'more_body': False})
