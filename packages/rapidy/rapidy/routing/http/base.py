from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from rapidy_core.exceptions import RapidyException

if TYPE_CHECKING:
    from rapidy import Rapidy

__all__ = ('BaseHTTPRouter', 'IncorrectPathError', 'RouterTypeError', 'raise_if_not_base_http_router')


class RouterTypeError(RapidyException):
    """Raised when an application receives a non-router object."""

    message = """
    `route_handler` must be a subclass of `BaseHTTPRouter`

    Examples:
    >>> from rapidy.http import get
    >>> @get('/users/{user_id}')
    >>> async def some_get(user_id: str) -> None:
    >>>     pass
    """


class IncorrectPathError(RapidyException):
    """Raised when a route path does not begin with a slash."""

    message = 'Attribute `path` must start with a slash `/`, not `{path}`.'


class BaseHTTPRouter(ABC):
    """Base contract for objects that register HTTP routes."""

    __slots__ = ('path',)

    def __init__(self, path: str | None) -> None:
        if path is not None and not path.startswith('/'):
            raise IncorrectPathError(path=path)
        self.path = path

    @abstractmethod
    def route_register(self, application: Rapidy) -> None:
        """Register this object in an application."""
        raise NotImplementedError


def raise_if_not_base_http_router(obj: Any) -> None:
    """Validate one route-registration object."""
    if not isinstance(obj, BaseHTTPRouter):
        raise RouterTypeError
