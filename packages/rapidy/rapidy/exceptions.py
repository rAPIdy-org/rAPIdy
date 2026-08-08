from __future__ import annotations

from collections.abc import Iterable, Mapping
from http import HTTPStatus
from typing import Any

from multidict import CIMultiDict
from rapidy_core.exceptions import RapidyException

from rapidy.typedefs import LooseHeaders

__all__ = (
    'ASGIProtocolError',
    'HTTPException',
    'HTTPMethodNotAllowed',
    'HTTPNotFound',
    'ResponseDuplicateBodyError',
    'ResponseEncodeError',
    'RouteConflictError',
)


class ASGIProtocolError(RapidyException):
    """Raised when an ASGI peer sends an unexpected event."""


class RouteConflictError(RapidyException):
    """Raised when a method/path pair is registered twice."""


class ResponseDuplicateBodyError(RapidyException):
    """Raised when both compatibility body inputs are provided."""


class ResponseEncodeError(RapidyException):
    """Reserved for full response serialization in milestone 10."""


# TODO(09-exceptions-full): replace with the complete §5.7 hierarchy without changing constructors.  # noqa: FIX002
class HTTPException(Exception):  # noqa: N818
    """Minimal HTTP error contract used by the matcher and dispatcher."""

    status_code: int = -1

    def __init__(
        self,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.reason = reason or HTTPStatus(self.status_code).phrase
        self.text = text if text is not None else f'{self.status_code}: {self.reason}'
        self.body = body if body is not None else self.text
        self.content_type = content_type or 'text/plain'
        if headers is None:
            self.headers: CIMultiDict[str] = CIMultiDict()
        elif isinstance(headers, Mapping):
            self.headers = CIMultiDict(headers)
        else:
            self.headers = CIMultiDict(
                (
                    key.decode('latin-1') if isinstance(key, bytes) else key,
                    value.decode('latin-1') if isinstance(value, bytes) else value,
                )
                for key, value in headers
            )
        super().__init__(self.text)


class HTTPNotFound(HTTPException):
    """Resource path was not registered."""

    status_code = HTTPStatus.NOT_FOUND


class HTTPMethodNotAllowed(HTTPException):
    """Resource exists, but not for the requested method."""

    status_code = HTTPStatus.METHOD_NOT_ALLOWED

    def __init__(
        self,
        method: str,
        allowed_methods: Iterable[str],
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.method = method
        self.allowed_methods = set(allowed_methods)
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self.headers['Allow'] = ', '.join(sorted(self.allowed_methods))
