from __future__ import annotations

from functools import cached_property
from typing import Any

from attrs import define

from rapidy.endpoint_handlers.attr_containers import DataAttr
from rapidy.enums import HTTPRequestParamType
from rapidy.parameters.http import RequestParamFieldInfo


@define(slots=True)
class HTTPRequestAttr(DataAttr):
    """Represents an HTTP request parameter attribute.

    Inherits from `DataAttr` and extends it by adding HTTP-specific
    information such as the parameter type and how to extract it.

    Attributes:
        field_info (RequestParamFieldInfo): Information about the HTTP request parameter.
    """

    field_info: RequestParamFieldInfo

    @classmethod
    def create_by_data_attr(cls, data_attr: DataAttr) -> HTTPRequestAttr:
        """Creates an instance of `HTTPRequestAttr` using a `DataAttr` instance.

        Args:
            data_attr (DataAttr): A `DataAttr` instance that provides attribute information.

        Returns:
            HTTPRequestAttr: A new instance of `HTTPRequestAttr` created from `data_attr`.

        Raises:
            AssertionError: If `data_attr.field_info` is not an instance of `RequestParamFieldInfo`.
        """
        assert isinstance(data_attr.field_info, RequestParamFieldInfo)  # noqa: S101

        return cls(
            attribute_name=data_attr.attribute_name,
            attribute_idx=data_attr.attribute_idx,
            attribute_annotation=data_attr.attribute_annotation,
            field_info=data_attr.field_info,
        )

    @cached_property
    def field_annotation(self) -> Any:
        """Gets the annotation of the HTTP request parameter.

        Returns:
            Any: The annotation of the HTTP request parameter.
        """
        return self.field_info.annotation

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        """Gets the type of the HTTP request parameter.

        Returns:
            HTTPRequestParamType: The type of the HTTP request parameter (e.g., query, body, path, etc.).
        """
        return self.field_info.param_type

    @cached_property
    def extract_as_single_param(self) -> bool:
        """Indicates whether the parameter should be extracted as a single parameter.

        Returns:
            bool: True if the parameter should be extracted as a single parameter, otherwise False.
        """
        return self.field_info.extract_single
