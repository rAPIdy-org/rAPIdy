from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from types import MappingProxyType
from typing import Any

from rapidy.exceptions import HTTPException, HTTPValidationFailure
from rapidy.request import Request
from rapidy.response import Response
from rapidy.typedefs import HTTPResponse

__all__ = ('ExceptionHandler', 'ProblemDetails', 'ProblemDetailsRenderer')

type ExceptionHandler = Callable[[Request, Exception], HTTPResponse | Awaitable[HTTPResponse]]

_RESERVED_MEMBERS = frozenset({'type', 'title', 'status', 'detail', 'instance'})
_MIN_HTTP_STATUS = 100
_MAX_HTTP_STATUS = 599


@dataclass(frozen=True, slots=True)
class ProblemDetails:
    """RFC 9457 problem detail document with extension-member support."""

    title: str
    status: int
    type: str = 'about:blank'
    detail: str | None = None
    instance: str | None = None
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.title:
            msg = 'Problem Details title must not be empty'
            raise ValueError(msg)
        if not _MIN_HTTP_STATUS <= self.status <= _MAX_HTTP_STATUS:
            msg = 'Problem Details status must be between 100 and 599'
            raise ValueError(msg)
        if not self.type:
            msg = 'Problem Details type must not be empty'
            raise ValueError(msg)
        conflict = _RESERVED_MEMBERS.intersection(self.extensions)
        if conflict:
            msg = f'Problem Details extension conflicts with reserved member: {min(conflict)}'
            raise ValueError(msg)
        object.__setattr__(self, 'extensions', MappingProxyType(dict(self.extensions)))

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready representation, omitting absent optional members."""
        document: dict[str, Any] = {'type': self.type, 'title': self.title, 'status': self.status}
        if self.detail is not None:
            document['detail'] = self.detail
        if self.instance is not None:
            document['instance'] = self.instance
        document.update(self.extensions)
        return document


class ProblemDetailsRenderer:
    """Render HTTP and application exceptions as ``application/problem+json``."""

    __slots__ = ('_expose_internal_details', '_type_base_url')

    def __init__(self, *, expose_internal_details: bool = False, type_base_url: str | None = None) -> None:
        if type_base_url is not None and not type_base_url.rstrip('/'):
            msg = 'Problem Details type base URL must not be empty'
            raise ValueError(msg)
        self._expose_internal_details = expose_internal_details
        self._type_base_url = type_base_url.rstrip('/') if type_base_url is not None else None

    def __call__(self, request: Request, exception: Exception) -> Response:
        """Convert an exception into an RFC 9457 response."""
        if isinstance(exception, HTTPException):
            status = exception.status_code
            if status < HTTPStatus.BAD_REQUEST:
                return _http_control_response(exception)
            title = exception.reason or _status_title(status)
            if isinstance(exception, HTTPValidationFailure):
                detail = None
                extensions = {
                    exception.validation_failure_field_name: [dict(error) for error in exception.validation_errors],
                }
            else:
                detail = exception.text
                extensions = {}
            headers = exception.headers
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            title = HTTPStatus.INTERNAL_SERVER_ERROR.phrase
            detail = str(exception) if self._expose_internal_details else None
            extensions = {}
            headers = None
        problem_type = 'about:blank'
        if self._type_base_url is not None:
            problem_type = f'{self._type_base_url}/{int(status)}'
        problem = ProblemDetails(
            type=problem_type,
            title=title,
            status=int(status),
            detail=detail,
            instance=str(request.scope.get('path', request.path)),
            extensions=extensions,
        )
        return Response(
            problem.as_dict(),
            status=int(status),
            headers=headers,
            content_type='application/problem+json',
        )


def _http_control_response(exception: HTTPException) -> Response:
    content_type = exception.content_type
    if content_type is None and exception.text is not None:
        content_type = 'text/plain'
    if exception.body is not None:
        return Response(
            exception.body,
            status=exception.status_code,
            headers=exception.headers,
            content_type=content_type,
            reason=exception.reason,
        )
    return Response(
        status=exception.status_code,
        headers=exception.headers,
        text=exception.text,
        content_type=content_type,
        reason=exception.reason,
    )


def _status_title(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return 'HTTP Error'
