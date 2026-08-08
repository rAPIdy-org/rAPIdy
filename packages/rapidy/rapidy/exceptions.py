from __future__ import annotations

from rapidy_core.exceptions import RapidyException

__all__ = (
    'ASGIProtocolError',
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
