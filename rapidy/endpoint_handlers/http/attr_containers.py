from functools import cached_property
from typing import Any

from attrs import define

from rapidy.endpoint_handlers.attr_containers import DataAttr
from rapidy.enums import HTTPRequestParamType
from rapidy.parameters.http import RequestParamFieldInfo


@define(slots=True)
class HTTPRequestAttr(DataAttr):
    field_info: RequestParamFieldInfo

    @classmethod
    def create_by_data_attr(cls, data_attr: DataAttr) -> 'HTTPRequestAttr':
        assert isinstance(data_attr.field_info, RequestParamFieldInfo)

        return cls(
            attribute_name=data_attr.attribute_name,
            attribute_idx=data_attr.attribute_idx,
            attribute_annotation=data_attr.attribute_annotation,
            field_info=data_attr.field_info,
        )

    @cached_property
    def field_annotation(self) -> Any:
        return self.field_info.annotation

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        return self.field_info.param_type

    @cached_property
    def extract_as_single_param(self) -> bool:
        return self.field_info.extract_single
