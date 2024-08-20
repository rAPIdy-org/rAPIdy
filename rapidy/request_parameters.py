from abc import ABC
from decimal import Decimal
from functools import cached_property
from inspect import isclass
from typing import Any, Dict, Optional

from aiohttp import StreamReader
from aiohttp.typedefs import DEFAULT_JSON_DECODER, JSONDecoder

from rapidy._annotation_helpers import get_base_annotations
from rapidy._request_param_model_field import ParamFieldInfo
from rapidy.request_enums import BodyType, HTTPRequestParamType
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

    _base_annotation_body_type_map: Dict[Any, BodyType] = {
        str: BodyType.text,
        int: BodyType.text,
        float: BodyType.text,
        Decimal: BodyType.text,
        bytes: BodyType.binary,
        StreamReader: BodyType.binary,
    }

    def __init__(
            self,
            default: Any = Undefined,
            *,
            default_factory: Optional[NoArgAnyCallable] = None,
            validate: bool = True,
            body_type: Optional[BodyType] = None,  # default: json
            check_content_type: Optional[bool] = None,  # default: True
            json_decoder: Optional[JSONDecoder] = None,  # default: json.loads
            **field_info_kwargs: Any,
    ) -> None:
        super().__init__(default=default, default_factory=default_factory, validate=validate, **field_info_kwargs)
        self._body_type = body_type
        self._json_decoder = json_decoder
        self._check_content_type = check_content_type
        self._body_type_by_default_not_support_check_content_type = False

    @cached_property
    def can_default(self) -> bool:  # type: ignore[override]
        return not self._annotation_is_stream_reader()

    @cached_property
    def check_content_type(self) -> bool:
        if self._body_type_by_default_not_support_check_content_type:
            return False if self._check_content_type is None else self._check_content_type

        return True if self._check_content_type is None else self._check_content_type

    @cached_property
    def body_type(self) -> BodyType:
        return self._body_type if self._body_type is not None else self._create_default_body_type()

    @cached_property
    def need_validate(self) -> bool:
        annotation_is_stream_reader = self._annotation_is_stream_reader()
        if annotation_is_stream_reader:
            return False
        return self._need_validate if self._need_validate is not None else True

    @cached_property
    def json_decoder(self) -> Optional[JSONDecoder]:
        if self.body_type == BodyType.json:
            if self._json_decoder is None:
                return DEFAULT_JSON_DECODER
            return self._json_decoder
        return None

    def _annotation_is_stream_reader(self) -> bool:
        assert self.annotation

        base_annotations = get_base_annotations(self.annotation)
        return any((base_annotation == StreamReader for base_annotation in base_annotations))

    def _create_default_body_type(self) -> BodyType:
        assert self.annotation

        base_annotations = get_base_annotations(self.annotation)

        for base_annotation in base_annotations:
            if isclass(base_annotation):
                for body_type in self._base_annotation_body_type_map:  # noqa: WPS528
                    if issubclass(base_annotation, body_type):
                        self._body_type_by_default_not_support_check_content_type = True
                        return self._base_annotation_body_type_map[body_type]

            elif base_annotation in self._base_annotation_body_type_map:
                # Protection against cases when user specifies Union[str, bytes] -
                # expected data type will be defined as first in order.
                self._body_type_by_default_not_support_check_content_type = True
                return self._base_annotation_body_type_map[base_annotation]

        return BodyType.json
