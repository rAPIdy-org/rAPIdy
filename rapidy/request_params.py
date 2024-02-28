import inspect
from abc import ABC
from copy import copy
from functools import partial
from typing import Any, Optional

from aiohttp.typedefs import DEFAULT_JSON_DECODER, JSONDecoder

from rapidy._extractors import (
    extract_body_bytes,
    extract_body_json,
    extract_body_multi_part,
    extract_body_stream,
    extract_body_text,
    extract_body_x_www_form,
    extract_cookies,
    extract_headers,
    extract_path,
    extract_query,
)
from rapidy._request_params_base import ParamType, ValidateType
from rapidy.constants import MAX_BODY_SIZE
from rapidy.fields import create_field, get_annotation_from_field_info, ModelField, ParamFieldInfo
from rapidy.media_types import ApplicationBytes, ApplicationJSON, ApplicationXWWWForm, MultipartForm, TextPlain

__all__ = (
    'BytesBody',
    'Cookie',
    'CookieSchema',
    'CookieRaw',
    'FormDataBody',
    'FormDataBodySchema',
    'FormDataBodyRaw',
    'Header',
    'HeaderSchema',
    'HeaderRaw',
    'JsonBody',
    'JsonBodySchema',
    'JsonBodyRaw',
    'MultipartBody',
    'MultipartBodySchema',
    'MultipartBodyRaw',
    'Path',
    'PathSchema',
    'PathRaw',
    'Query',
    'QuerySchema',
    'QueryRaw',
    'StreamBody',
    'TextBody',
)

from rapidy.typedefs import Required


class BodyParamAttrDefinitionError(Exception):
    pass


class DefaultDefinitionError(Exception):
    pass


class PathBase(ParamFieldInfo):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs, param_type=ParamType.path, extractor=extract_path, can_default=False)


class Path(PathBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.param)


class PathSchema(PathBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class PathRaw(PathBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class HeaderBase(ParamFieldInfo):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, param_type=ParamType.header, extractor=extract_headers)


class Header(HeaderBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.param)


class HeaderSchema(HeaderBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class HeaderRaw(HeaderBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class CookieBase(ParamFieldInfo):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, param_type=ParamType.cookie, extractor=extract_cookies)


class Cookie(CookieBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.param)


class CookieSchema(CookieBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class CookieRaw(CookieBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class QueryBase(ParamFieldInfo):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, param_type=ParamType.query, extractor=extract_query)


class Query(QueryBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.param)


class QuerySchema(QueryBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class QueryRaw(QueryBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class BodyBase(ParamFieldInfo, ABC):
    def __init__(
            self,
            media_type: str,
            *,
            extractor: Any,
            body_max_size: Optional[int] = None,
            **kwargs: Any,
    ) -> None:
        self.body_max_size = body_max_size or MAX_BODY_SIZE
        self.media_type = media_type

        extractor = partial(extractor, max_size=self.body_max_size)

        super().__init__(
            **kwargs,
            extractor=extractor,
            param_type=ParamType.body,
        )


class StreamBody(BodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            **kwargs,
            validate_type=ValidateType.no_validate,
            extractor=extract_body_stream,
            media_type=ApplicationBytes,
            can_default=False,
        )


class BytesBody(BodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            **kwargs,
            validate_type=ValidateType.no_validate,
            extractor=extract_body_bytes,
            media_type=ApplicationBytes,
        )


class TextBody(BodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            **kwargs,
            validate_type=ValidateType.no_validate,
            extractor=extract_body_text,
            media_type=TextPlain,
        )


class JsonBodyBase(BodyBase):
    def __init__(
            self,
            *,
            json_decoder: Optional[JSONDecoder] = None,
            body_max_size: Optional[int] = None,
            **kwargs: Any,
    ) -> None:
        extractor = partial(
            extract_body_json,
            json_decoder=json_decoder or DEFAULT_JSON_DECODER,
        )

        super().__init__(
            **kwargs,
            body_max_size=body_max_size,
            extractor=extractor,
            media_type=ApplicationJSON,
        )


class JsonBody(JsonBodyBase):
    def __init__(
            self,
            *,
            body_max_size: Optional[int] = None,
            json_decoder: Optional[JSONDecoder] = None,
            **kwargs: Any,
    ) -> None:
        if body_max_size is not None or json_decoder is not None:
            raise BodyParamAttrDefinitionError(
                'A single JsonBody parameter does not allow to determine `body_max_size` or `json_decoder`. '
                'Please use JsonSchema or JsonRaw.',
            )

        super().__init__(
            **kwargs,
            validate_type=ValidateType.param,
            body_max_size=body_max_size,
            json_decoder=json_decoder,
        )


class JsonBodySchema(JsonBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class JsonBodyRaw(JsonBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class FormDataBodyBase(BodyBase):
    def __init__(
            self,
            *,
            attrs_case_sensitive: Optional[bool] = None,
            duplicated_attrs_parse_as_array: Optional[bool] = None,
            **kwargs: Any,
    ) -> None:
        extractor = partial(
            extract_body_x_www_form,
            attrs_case_sensitive=attrs_case_sensitive or False,
            duplicated_attrs_parse_as_array=duplicated_attrs_parse_as_array or False,
        )

        super().__init__(
            **kwargs,
            extractor=extractor,
            media_type=ApplicationXWWWForm,
        )


class FormDataBody(FormDataBodyBase):
    def __init__(
            self,
            *,
            body_max_size: Optional[int] = None,
            attrs_case_sensitive: Optional[bool] = None,
            duplicated_attrs_parse_as_array: Optional[bool] = None,
            **kwargs: Any,
    ) -> None:
        if (
            body_max_size is not None
            or attrs_case_sensitive is not None
            or duplicated_attrs_parse_as_array is not None
        ):
            raise BodyParamAttrDefinitionError(
                'A single FormDataBody parameter does not allow to determine '
                '`body_max_size` or `attrs_case_sensitive` or `duplicated_attrs_parse_as_array`. '
                'Please use FormDataSchema or FormDataRaw.',
            )

        super().__init__(**kwargs, validate_type=ValidateType.param)


class FormDataBodySchema(FormDataBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class FormDataBodyRaw(FormDataBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


class MultipartBodyBase(BodyBase):
    def __init__(
            self,
            attrs_case_sensitive: bool = False,
            duplicated_attrs_parse_as_array: bool = False,
            **kwargs: Any,
    ) -> None:
        extractor = partial(
            extract_body_multi_part,
            attrs_case_sensitive=attrs_case_sensitive,
            duplicated_attrs_parse_as_array=duplicated_attrs_parse_as_array,
        )

        super().__init__(
            **kwargs,
            extractor=extractor,
            media_type=MultipartForm,
        )


class MultipartBody(MultipartBodyBase):
    def __init__(
            self,
            *,
            body_max_size: Optional[int] = None,
            attrs_case_sensitive: Optional[bool] = None,
            duplicated_attrs_parse_as_array: Optional[bool] = None,
            **kwargs: Any,
    ) -> None:
        if (
            body_max_size is not None
            or attrs_case_sensitive is not None
            or duplicated_attrs_parse_as_array is not None
        ):
            raise BodyParamAttrDefinitionError(
                'A single MultipartBody parameter does not allow to determine '
                '`body_max_size` or `attrs_case_sensitive` or `duplicated_attrs_parse_as_array`. '
                'Please use MultipartBodySchema or MultipartBodyRaw.',
            )

        super().__init__(**kwargs, validate_type=ValidateType.param)


class MultipartBodySchema(MultipartBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.schema)


class MultipartBodyRaw(MultipartBodyBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, validate_type=ValidateType.no_validate)


def create_param_model_field_by_request_param(
        *,
        annotated_type: Any,
        field_info: ParamFieldInfo,
        param_name: str,
        param_default: Any,
) -> ModelField:
    copied_field_info = copy(field_info)

    if param_default is not inspect.Signature.empty:
        copied_field_info.default = param_default
    else:
        copied_field_info.default = Required

    inner_attribute_type = get_annotation_from_field_info(
        annotation=annotated_type,
        field_info=field_info,
        field_name=param_name,
    )

    return create_field(
        name=param_name,
        type_=inner_attribute_type,
        field_info=copied_field_info,
    )
