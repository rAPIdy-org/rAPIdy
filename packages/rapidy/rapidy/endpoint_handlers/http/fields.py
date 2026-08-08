from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from rapidy_core.fields import create_model_field, RapidyModelField

if TYPE_CHECKING:
    from rapidy_core.enums import HTTPRequestParamType
    from rapidy_core.parameters.http import RequestParamFieldInfo

__all__ = ('RequestModelField', 'create_request_model_field')


class RequestModelField(RapidyModelField):
    """Shared core model field enriched with its HTTP source."""

    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        """Return the request source associated with the marker."""
        return self.field_info.param_type


def create_request_model_field(field_info: RequestParamFieldInfo) -> RequestModelField:
    """Build an HTTP-aware model field through the shared core factory."""
    return create_model_field(field_info=field_info, class_=RequestModelField)
