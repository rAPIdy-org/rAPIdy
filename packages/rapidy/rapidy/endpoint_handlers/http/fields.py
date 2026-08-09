from __future__ import annotations

from functools import cached_property

from rapidy_core.annotation_checkers import is_multi_value_annotation
from rapidy_core.enums import HTTPRequestParamType  # noqa: TC002 - runtime annotations
from rapidy_core.fields import create_model_field, RapidyModelField
from rapidy_core.parameters.http import RequestParamFieldInfo  # noqa: TC002 - runtime annotations

__all__ = ('RequestModelField', 'create_request_model_field')


class RequestModelField(RapidyModelField):
    """Shared core model field enriched with its HTTP source."""

    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        """Return the request source associated with the marker."""
        return self.field_info.param_type

    @cached_property
    def accepts_multiple_values(self) -> bool:
        """Return whether repeated wire values form this field's collection input."""
        return is_multi_value_annotation(self.type_)


def create_request_model_field(field_info: RequestParamFieldInfo) -> RequestModelField:
    """Build an HTTP-aware model field through the shared core factory."""
    return create_model_field(field_info=field_info, class_=RequestModelField)
