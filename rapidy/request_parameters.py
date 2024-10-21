from abc import ABC
from functools import cached_property
from typing import Any, Optional, Union

from aiohttp import StreamReader
from aiohttp.typedefs import DEFAULT_JSON_DECODER, JSONDecoder

from rapidy._annotation_helpers import get_base_annotations
from rapidy._endpoint_model_field import ParamFieldInfo
from rapidy.enums import ContentType, HTTPRequestParamType
from rapidy.typedefs import NoArgAnyCallable, Undefined

__all__ = (
    'PathParam',
    'PathParams',
    'Header',
    'Headers',
    'Cookie',
    'Cookies',
    'QueryParam',
    'QueryParams',
    'Body',
)


# PATH

class PathBase(ParamFieldInfo, ABC):
    http_request_param_type = HTTPRequestParamType.path
    can_default = False


class PathParam(PathBase):
    extract_all = False


class PathParams(PathBase):
    extract_all = True


# HEADERS

class HeaderBase(ParamFieldInfo, ABC):
    http_request_param_type = HTTPRequestParamType.header
    can_default = True


class Header(HeaderBase):
    extract_all = False


class Headers(HeaderBase):
    extract_all = True


# COOKIES

class CookieBase(ParamFieldInfo):
    http_request_param_type = HTTPRequestParamType.cookie
    can_default = True


class Cookie(CookieBase):
    extract_all = False


class Cookies(CookieBase):
    extract_all = True


# QUERY PARAMS

class QueryBase(ParamFieldInfo):
    http_request_param_type = HTTPRequestParamType.query
    can_default = True


class QueryParam(QueryBase):
    extract_all = False


class QueryParams(QueryBase):
    extract_all = True


# BODY

class Body(ParamFieldInfo):
    http_request_param_type = HTTPRequestParamType.body
    extract_all = True

    def __init__(
            self,
            default: Any = Undefined,
            *,
            default_factory: Optional[NoArgAnyCallable] = None,
            validate: bool = True,
            content_type: Union[str, ContentType] = ContentType.json,
            check_content_type: bool = True,
            json_decoder: JSONDecoder = DEFAULT_JSON_DECODER,
            **pydantic_field_info_kwargs: Any,
    ) -> None:
        """Initialises the instance of `Body`.

        Args:
            default:
                The default value of the field.
            default_factory:
                The factory function used to construct the default for the field.
            validate:
                Flag determines whether the handler request should be validated.
            content_type:
                Expected value of the `Content-Type` of the header.
            check_content_type:
                Flag determines whether the incoming `Content-Type` header should be checked.
            json_decoder:
                Json decoder. Used if content_type=‘application/json’
            pydantic_field_info_kwargs:
                Additional validation parameters for pydantic field.
                https://docs.pydantic.dev/latest/api/fields/
        """
        super().__init__(
            default=default, default_factory=default_factory, validate=validate, **pydantic_field_info_kwargs,
        )
        self.content_type = content_type
        self.json_decoder = json_decoder
        self.check_content_type = check_content_type

    @cached_property
    def can_default(self) -> bool:  # type: ignore[override]
        return not self._annotation_is_stream_reader()

    @cached_property
    def need_validate(self) -> bool:
        annotation_is_stream_reader = self._annotation_is_stream_reader()
        if annotation_is_stream_reader:
            return False
        return self._need_validate if self._need_validate is not None else True

    def _annotation_is_stream_reader(self) -> bool:
        assert self.annotation

        base_annotations = get_base_annotations(self.annotation)
        return any((base_annotation == StreamReader for base_annotation in base_annotations))
