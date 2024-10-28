import dataclasses
from concurrent.futures import Executor
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union

from aiohttp import Payload
from aiohttp.helpers import parse_mimetype
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder, LooseHeaders
from aiohttp.web_response import ContentCoding, Response as AioHTTPResponse, StreamResponse
from pydantic import BaseModel

from rapidy._base_exceptions import RapidyException, RapidyHandlerException
from rapidy.encoders import CustomEncoder, Exclude, Include, jsonify
from rapidy.enums import Charset, ContentType, HeaderName

__all__ = (
    'ContentCoding',
    'StreamResponse',
    'Response',
)


class ResponseEncodeError(RapidyHandlerException):
    message = 'Encoding errors: \n {errors}'


class ResponseDataNotStrError(RapidyException):
    message = 'Json response data is not str. Use (dumps=True, ...) attribute to convert obj to str.'


class Response(AioHTTPResponse):
    def __init__(
            self,
            *,
            body: Any = None,
            status: int = 200,
            reason: Optional[str] = None,
            text: Optional[str] = None,
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
    ) -> None:
        if isinstance(charset, Enum):
            charset = charset.value

        if isinstance(content_type, Enum):
            content_type = content_type.value

        self._rapidy_charset = charset or Charset.utf8.value
        self._rapidy_content_type = content_type

        self._json_encoder = json_encoder

        self._include_fields = include
        self._exclude_fields = exclude
        self._by_alias = by_alias
        self._exclude_unset = exclude_unset
        self._exclude_defaults = exclude_defaults
        self._exclude_none = exclude_none
        self._custom_encoder = custom_encoder

        super().__init__(
            body=body,
            status=status,
            reason=reason,
            text=text,
            headers=headers,
            content_type=content_type,
            charset=charset,
            zlib_executor=zlib_executor,
            zlib_executor_size=zlib_executor_size,
        )

    @property
    def body(self) -> Optional[Union[bytes, Payload]]:
        return super(self.__class__, self.__class__).body  # noqa: WPS608

    @body.setter
    def body(self, body: Optional[Any]) -> None:
        if body is None or isinstance(body, bytes):
            super(self.__class__, self.__class__).body.fset(self, body)  # noqa: WPS608
            return

        current_content_type = self._rapidy_content_type
        if current_content_type is None:
            current_content_type = self._get_content_type_by_data(body).value

        ctype_obj = parse_mimetype(current_content_type)

        if ctype_obj.type == 'application' and ctype_obj.subtype == 'json':
            self._process_json_body(body)

        elif ctype_obj.type == 'text':
            self._process_text_body(body)

        else:
            self._process_bytes_body(body)

        self.headers[HeaderName.content_type.value] = f'{current_content_type}; charset={self._rapidy_charset}'

    def _process_json_body(self, body: Any) -> None:
        self.text = self._prepare_body_data(body, charset=self._rapidy_charset)

    def _process_text_body(self, body: Any) -> None:
        if not isinstance(body, str):
            body = self._prepare_body_data(body, charset=self._rapidy_charset, dumps=False)
            if not isinstance(body, str):
                body = self._json_encoder(body)

        self.text = body

    def _process_bytes_body(self, body: Any) -> None:
        if not isinstance(body, str):
            body = self._prepare_body_data(body, charset=self._rapidy_charset)

        self.body = body.encode(self._rapidy_charset)

    def _prepare_body_data(self, obj: Any, *, charset: str, dumps: bool = True) -> str:
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

    def _get_content_type_by_data(self, data: Any) -> ContentType:
        if isinstance(data, (BaseModel, dict)) or dataclasses.is_dataclass(data):
            return ContentType.json

        if isinstance(data, (str, Enum, int, float, Decimal, bool)):
            return ContentType.text_plain

        return ContentType.stream
