import dataclasses
from concurrent.futures import Executor
from decimal import Decimal
from enum import Enum
from typing import Any, Counter, DefaultDict, Optional, Tuple, Type, Union

from aiohttp import Payload
from aiohttp.helpers import parse_mimetype
from aiohttp.typedefs import LooseHeaders
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
    message = '`body` and `text` are not allowed together'


class ResponseEncodeError(RapidyException):
    message = 'Encoding errors: \n {errors}'


class Response(AioHTTPResponse):
    """Overridden aiohttp Response."""

    def __init__(
        self,
        body: Optional[Any] = None,
        *,
        status: int = 200,
        headers: Optional[LooseHeaders] = None,
        content_type: Union[str, ContentType, None] = None,
        charset: Optional[Union[str, Charset]] = None,
        zlib_executor: Optional[Executor] = None,
        zlib_executor_size: Optional[int] = None,
        # body preparer
        include: Optional[Include] = None,
        exclude: Optional[Exclude] = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        custom_encoder: Optional[CustomEncoder] = None,
        json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
        # backwards compatibility
        text: Optional[Any] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Low-level response factory.

        Args:
            body:
                Response body.
            text:
                Response text body.
                This attribute is not necessary, it is left for backwards compatibility with `aiohttp`.
                Please use the `body` attribute.
            reason:
                Response reason.
                This attribute is not necessary, it is left for backwards compatibility with `aiohttp`.
            status:
                Response http status code.
            headers:
                Additional response headers.
            content_type:
                Expected value of the `Content-Type` of the header.
            charset:
                The `charset` that will be used to encode and decode body data.
            zlib_executor:
                Executor to use for zlib compression
            zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            include:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            exclude:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True.
        """
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

        body_exists = body is not None
        text_exists = text is not None

        if body_exists and text_exists:
            raise ResponseDuplicateBodyError

        if body_exists:
            self.body = body

        if text_exists:
            self.text = text

    @property
    def body(self) -> Optional[Union[bytes, Payload]]:
        """Read attribute for storing response`s content aka BODY, bytes."""
        return self._super.body

    @body.setter
    def body(self, body: Optional[Any]) -> None:
        """Write attribute for storing response`s content aka BODY, bytes."""
        if body is None or isinstance(body, bytes):
            self._super.body.fset(self, body)
            return

        self._set_body(body)

    @property
    def text(self) -> Optional[Union[bytes, Payload]]:
        """Read attribute for storing response`s body, represented as str."""
        return self._super.text

    @text.setter
    def text(self, text: Optional[Any]) -> None:
        """Write attribute for storing response`s body, represented as str."""
        if text is None or isinstance(text, str):
            self._set_text(text)
            return

        self._set_body(text)

    def _set_body(self, body: Optional[Any]) -> None:
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

    def _set_text(self, text: Optional[str]) -> None:
        self._super.text.fset(self, text)

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

    @property
    def _super(self) -> Any:
        return super(self.__class__, self.__class__)
