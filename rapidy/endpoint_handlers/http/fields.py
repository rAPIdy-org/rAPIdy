from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast, Dict, Optional

from rapidy.endpoint_handlers.http.annotation_checkers import is_stream_reader
from rapidy.enums import HTTPRequestParamType
from rapidy.fields.model_fields import ABCRapidyModelField, create_model_field, RapidyModelField
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.typedefs import LocStr, ModelOrDc, Undefined, ValidateReturn


class RequestModelField(RapidyModelField):
    field_info: RequestParamFieldInfo
    http_param_type: HTTPRequestParamType


class _RequestModelField(RapidyModelField):
    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        return self.field_info.param_type


@dataclass
class StreamReaderModelField(ABCRapidyModelField):
    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        return self.field_info.param_type

    @cached_property
    def required(self) -> bool:
        return True

    @cached_property
    def default(self) -> Any:
        return Undefined

    @cached_property
    def need_validate(self) -> bool:
        return False

    @cached_property
    def get_default(self) -> Any:
        return Undefined

    def validate(
        self,
        value: Any,
        values: Dict[str, Any],
        *,
        loc: LocStr,
        cls: Optional[ModelOrDc] = None,
    ) -> ValidateReturn:
        raise NotImplementedError


def create_stream_reader_model_field(field_info: RequestParamFieldInfo) -> StreamReaderModelField:
    return StreamReaderModelField(name=field_info.name, field_info=field_info)


def create_request_model_field(field_info: RequestParamFieldInfo) -> RequestModelField:
    if field_info.param_type == HTTPRequestParamType.body and is_stream_reader(field_info.annotation):
        model_field = create_stream_reader_model_field(field_info=field_info)
    else:
        model_field = create_model_field(field_info=field_info, class_=_RequestModelField)

    return cast(RequestModelField, model_field)
