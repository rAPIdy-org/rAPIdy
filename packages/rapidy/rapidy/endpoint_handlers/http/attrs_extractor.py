from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rapidy_core.annotation_checkers import is_empty
from rapidy_core.parameters.http import RequestParamFieldInfo
from rapidy_core.signature import get_signature_raw_info

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.endpoint_handlers.attr_containers import Attr, DataAttr
from rapidy.endpoint_handlers.http.annotation_checkers import (
    annotation_is_request,
    annotation_is_stream_response,
)
from rapidy.endpoint_handlers.http.attr_containers import HTTPRequestAttr
from rapidy.typedefs import Handler

__all__ = ('HTTPHandlerInfo', 'RequestFieldAlreadyExistsError', 'get_http_handler_info')


class RequestFieldAlreadyExistsError(RapidyHandlerException):
    """Raised when Request injection is declared more than once."""

    message = (
        'Error during attribute definition in the handler - request param defined twice. '
        'The error may be because the first attribute of the handler is not annotated. '
        'By default, `rapidy` will pass `Request` to the first attribute if it has no type annotation.'
    )


@dataclass(slots=True)
class HTTPHandlerInfo:
    """Core signature information enriched with HTTP injection metadata."""

    return_annotation: Any
    attrs: list[Attr]
    data_attrs: list[DataAttr]
    request_attribute: Attr | None = None
    response_attribute: Attr | None = None
    request_params: list[HTTPRequestAttr] = field(default_factory=list)


def get_http_handler_info(
    handler: Handler,
    *,
    request_attr_can_declare_fst: bool,
) -> HTTPHandlerInfo:
    """Extract HTTP markers and Request/Response injection attributes."""
    raw = get_signature_raw_info(handler)
    info = HTTPHandlerInfo(
        return_annotation=raw.return_annotation,
        attrs=raw.attrs,
        data_attrs=raw.data_attrs,
    )

    for data_attr in raw.data_attrs:
        if isinstance(data_attr.field_info, RequestParamFieldInfo):
            info.request_params.append(HTTPRequestAttr.create_by_data_attr(data_attr))

    for attr in raw.attrs:
        if annotation_is_stream_response(attr.attribute_annotation):
            info.response_attribute = attr
        elif annotation_is_request(attr.attribute_annotation) or (
            request_attr_can_declare_fst
            and attr.attribute_idx == 0
            and is_empty(attr.attribute_annotation)
        ):
            if info.request_attribute is not None:
                raise RequestFieldAlreadyExistsError.create(handler=handler)
            info.request_attribute = attr

    return info
