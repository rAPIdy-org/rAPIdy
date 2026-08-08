from __future__ import annotations

import dataclasses
from concurrent.futures import Executor
from decimal import Decimal
from enum import Enum
from typing import Any, Counter, DefaultDict, Tuple, Type, TYPE_CHECKING

from aiohttp.helpers import parse_mimetype
from aiohttp.web_response import (
    Response as AioHTTPResponse,
    StreamResponse,
)
from pydantic import BaseModel

from rapidy._base_exceptions import RapidyException
from rapidy.constants import DEFAULT_JSON_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include, jsonify
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import JSONEncoder

if TYPE_CHECKING:
    from aiohttp import Payload
    from aiohttp.typedefs import LooseHeaders

__all__ = (
    'StreamResponse',
    'Response',
)

DEFAULT_JSON_TYPES: Tuple[Type[Any], ...] = (
    BaseModel,
    dict,
    list,
    tuple,
    set,
    frozenset,
    DefaultDict,
    Counter,
)

DEFAULT_TEXT_PLAIN_TYPES: Tuple[Type[Any], ...] = (
    str,
    Enum,
    int,
    float,
    Decimal,
    bool,
)


class ResponseDuplicateBodyError(RapidyException):
    """Exception raised when both 'body' and 'text' are provided together."""

    message = '`body` and `text` are not allowed together'


class ResponseEncodeError(RapidyException):
    """Exception raised when an error occurs during encoding."""

    message = 'Encoding errors: \n {errors}'


class Response(AioHTTPResponse):
    """Override for aiohttp Response class to handle various body types with advanced customization.

    Args:
        body (Optional[Any], optional): The response body. Defaults to None.
        text (Optional[Any], optional): The response text body, kept for backwards compatibility. Use `body` instead.
        reason (Optional[str], optional): The response reason for backwards compatibility. Defaults to None.
        status (int, optional): HTTP status code for the response. Defaults to 200.
        headers (Optional[LooseHeaders], optional): Additional headers for the response. Defaults to None.
        content_type (Union[str, ContentType, None], optional): The response Content-Type header. Defaults to None.
        charset (Optional[Union[str, Charset]], optional): Character encoding for body data. Defaults to None.
        zlib_executor (Optional[Executor], optional): Executor for zlib compression. Defaults to None.
        zlib_executor_size (Optional[int], optional): Size threshold in bytes for zlib compression. Defaults to None.
        include (Optional[Include], optional): Fields to include during serialization. Defaults to None.
        exclude (Optional[Exclude], optional): Fields to exclude during serialization. Defaults to None.
        by_alias (bool, optional): Whether to use aliases during serialization. Defaults to True.
        exclude_unset (bool, optional): Whether to exclude unset fields during serialization. Defaults to False.
        exclude_defaults (bool, optional): Whether to exclude fields with default values. Defaults to False.
        exclude_none (bool, optional): Whether to exclude fields with None values. Defaults to False.
        custom_encoder (Optional[CustomEncoder], optional): Custom encoder for Pydantic models. Defaults to None.
        json_encoder (JSONEncoder, optional): JSON encoder function. Defaults to the default encoder.

    Raises:
        ResponseDuplicateBodyError: If both `body` and `text` are provided.
        ResponseEncodeError: If an error occurs during the body encoding process.
    """

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
        """Initialize the response object with given parameters."""
        if isinstance(charset, Enum):
            charset = charset.value

        if isinstance(content_type, Enum):
            content_type = content_type.value

        self._json_encoder = json_encoder
        self._include_fields = include
        self._exclude_fields = exclude
        self._by_alias = by_alias
        self._exclude_unset = exclude_unset
        self._exclude_defaults = exclude_defaults
        self._exclude_none = exclude_none
        self._custom_encoder = custom_encoder

        super().__init__(
            status=status,
            reason=reason,
            headers=headers,
            content_type=content_type,
            charset=charset,
            zlib_executor=zlib_executor,
            zlib_executor_size=zlib_executor_size,
        )

        # Handle 'body' and 'text' together to raise an error if both are present
        body_exists = body is not None
        text_exists = text is not None

        if body_exists and text_exists:
            raise ResponseDuplicateBodyError

        if body_exists:
            self.body = body

        if text_exists:
            self.text = text

    @property
    def body(self) -> bytes | Payload | None:
        """Return the response body as bytes or payload."""
        return self._super.body

    @body.setter
    def body(self, body: Any | None) -> None:
        """Set the response body as bytes or other appropriate format."""
        if body is None or isinstance(body, bytes):
            self._super.body.fset(self, body)
            return

        self._set_body(body)

    @property
    def text(self) -> bytes | Payload | None:
        """Return the response body as text (string format)."""
        return self._super.text

    @text.setter
    def text(self, text: Any | None) -> None:
        """Set the response body as text (string format)."""
        if text is None or isinstance(text, str):
            self._set_text(text)
            return

        self._set_body(text)

    def _set_body(self, body: Any | None) -> None:
        """Helper function to set the body, handling different content types."""
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
        """Helper function to set text content."""
        self._super.text.fset(self, text)

    def _process_json_body(self, body: Any) -> None:
        """Process the body if it's a JSON type."""
        self._set_text(self._simplify_body(body, charset=self.charset))

    def _process_text_body(self, body: Any) -> None:
        """Process the body if it's a plain text type."""
        if not isinstance(body, str):
            body = self._simplify_body(body, charset=self.charset, dumps=False)
            if not isinstance(body, str):
                body = self._json_encoder(body)

        self._set_text(body)

    def _process_bytes_body(self, body: Any) -> None:
        """Process the body if it's binary data."""
        if not isinstance(body, str):
            body = self._simplify_body(body, charset=self.charset)

        self.body = body.encode(self.charset)

    def _simplify_body(self, obj: Any, *, charset: str, dumps: bool = True) -> str:
        """Simplify the body by serializing it into a string."""
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
        """Determine and set the Content-Type based on the data type."""
        if isinstance(data, DEFAULT_JSON_TYPES) or dataclasses.is_dataclass(data):
            self.content_type = ContentType.json.value
            return ContentType.json

        if isinstance(data, DEFAULT_TEXT_PLAIN_TYPES):
            return ContentType.text_plain

        return ContentType.stream

    @property
    def _super(self) -> Any:
        """Return the super class for calling the base class methods."""
        return super(self.__class__, self.__class__)
