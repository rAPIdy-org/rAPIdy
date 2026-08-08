from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from rapidy_core.parameters.http import RequestParamFieldInfo

from rapidy.endpoint_handlers.attr_containers import DataAttr

if TYPE_CHECKING:
    from rapidy_core.enums import HTTPRequestParamType

__all__ = ('HTTPRequestAttr',)


@dataclass(slots=True)
class HTTPRequestAttr:
    """HTTP-specific view over core signature field metadata."""

    attribute_name: str
    attribute_idx: int
    attribute_annotation: Any
    field_info: RequestParamFieldInfo

    @classmethod
    def create_by_data_attr(cls, data_attr: DataAttr) -> HTTPRequestAttr:
        """Create an HTTP attribute after checking the marker family."""
        if not isinstance(data_attr.field_info, RequestParamFieldInfo):
            msg = 'Expected RequestParamFieldInfo'
            raise TypeError(msg)
        return cls(
            attribute_name=data_attr.attribute_name,
            attribute_idx=data_attr.attribute_idx,
            attribute_annotation=data_attr.attribute_annotation,
            field_info=data_attr.field_info,
        )

    @property
    def field_annotation(self) -> Any:
        """Return the prepared field annotation."""
        return self.field_info.annotation

    @property
    def http_param_type(self) -> HTTPRequestParamType:
        """Return the source represented by this marker."""
        return self.field_info.param_type

    @property
    def extract_as_single_param(self) -> bool:
        """Return whether extraction addresses one named value."""
        return self.field_info.extract_single
