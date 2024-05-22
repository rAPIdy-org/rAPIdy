from abc import ABC
from typing import Any, Dict, Optional

from aiohttp import StreamReader
from aiohttp.typedefs import DEFAULT_JSON_DECODER, JSONDecoder

from rapidy._annotations.extractor_helpers import get_base_annotations
from rapidy._fields.model_field import ParamFieldInfo
from rapidy.request._enums import BodyType, HTTPRequestParamType
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
        bytes: BodyType.binary,
        StreamReader: BodyType.binary,
    }

    def __init__(
            self,
            default: Any = Undefined,
            *,
            default_factory: Optional[NoArgAnyCallable] = None,
            body_type: Optional[BodyType] = None,
            check_content_type: bool = True,
            json_decoder: Optional[JSONDecoder] = None,
            **field_info_kwargs: Any,
    ) -> None:
        super().__init__(default=default, default_factory=default_factory, **field_info_kwargs)
        self._body_type = body_type
        self._json_decoder = json_decoder
        self.check_content_type = check_content_type

    @property
    def can_default(self) -> bool:
        return not self._annotation_is_stream_reader()

    @property
    def body_type(self) -> BodyType:
        return self._body_type if self._body_type is not None else self._create_default_body_type()

    @property
    def validate(self) -> bool:
        annotation_is_stream_reader = self._annotation_is_stream_reader()
        if annotation_is_stream_reader:
            return False
        return self._validate if self._validate is not None else True

    @property
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
            if base_annotation in self._base_annotation_body_type_map:
                # Protection against cases when user specifies Union[str, bytes] -
                # expected data type will be defined as first in order.
                #
                # Maybe in the future there will be added support for multiple types for Body at once.
                self.check_content_type = False if self.check_content_type is None else None
                return self._base_annotation_body_type_map[base_annotation]

        return BodyType.json
