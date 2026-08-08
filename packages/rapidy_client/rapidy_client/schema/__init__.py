from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rapidy_core import UNSET, ContentType, Unset
from rapidy_core.parameters.http import (
    Body,
    Cookie,
    Cookies,
    Header,
    Headers,
    PathParam,
    PathParams,
    QueryParam,
    QueryParams,
)
from rapidy_core.typedefs import Undefined

from rapidy_client._models import AuthPolicy, Timeout

if TYPE_CHECKING:
    from rapidy_client.config import RetryConfig


class Form(Body):  # type: ignore[misc]
    """Form-urlencoded request body marker."""

    body_kind = "form"

    def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
        kwargs["content_type"] = ContentType.x_www_form
        super().__init__(default, **kwargs)


class File(Body):  # type: ignore[misc]
    """Multipart file request body marker."""

    body_kind = "file"

    def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
        kwargs["content_type"] = ContentType.m_part_form_data
        super().__init__(default, **kwargs)


class ListStyle(enum.Enum):
    REPEAT = "repeat"
    CSV = "csv"


@dataclass(slots=True, kw_only=True)
class QuerySerialization:
    list_style: ListStyle = ListStyle.REPEAT


@dataclass(slots=True, kw_only=True)
class CallOptions:
    timeout: Timeout | float | None | Unset = UNSET
    retry: RetryConfig | None | Unset = UNSET
    auth: AuthPolicy | None | Unset = UNSET
    headers: Mapping[str, str] | None = None
    deadline: float | Unset = UNSET
    follow_redirects: bool | Unset = UNSET


from rapidy_client.schema._binding import (
    Stream,
    controller,
    delete,
    get,
    head,
    options,
    patch,
    post,
    put,
)

__all__ = (
    "UNSET",
    "Body",
    "CallOptions",
    "Cookie",
    "Cookies",
    "File",
    "Form",
    "Header",
    "Headers",
    "ListStyle",
    "PathParam",
    "PathParams",
    "QueryParam",
    "QueryParams",
    "QuerySerialization",
    "Stream",
    "Unset",
    "controller",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
)
