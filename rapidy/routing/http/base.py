from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from rapidy._base_exceptions import RapidyException

if TYPE_CHECKING:
    from rapidy import Rapidy


class RouterTypeError(RapidyException):
    """Exception raised when `route_handler` is not a subclass of `BaseHTTPRouter`."""

    message = """
    `route_handler` must be a subclass of `BaseHTTPRouter`

    Examples:
    >>> from rapidy.http import get, controller, PathParam

    >>> @get("/{user_id}")  # <-- `get` deco
    >>> async def some_get(self, user_id: str = PathParam()) -> None:
    >>>    pass

    >>> @controller("/")  # <-- `controller` deco
    >>> class SomeController§(web.View):
    >>>     @get("/{user_id}")  # <-- `get` deco
    >>>     async def some_get(self, user_id: str = PathParam()) -> None:
    >>>         pass

    >>> api_router = HTTPRouter(
    >>>     '/api',
    >>>     route_handlers=[
    >>>     ],
    >>> )
    )
    """


class IncorrectPathError(RapidyException):
    """Exception raised when the 'path' attribute is incorrectly formatted.

    Attributes:
        message (str): Error message template that includes the incorrect path.
    """

    message = 'Attribute `path` must start with a slash `/`, not `{path}`.'


class BaseHTTPRouter(ABC):
    """Abstract base class for HTTP routers in the application.

    This class serves as a base for routers that handle routing logic for HTTP requests.
    It ensures the validity of the `path` attribute and defines an abstract method
    for route registration in a `Rapidy` application.

    Attributes:
        path (Optional[str]): The path for the router, which must start with a slash ('/').
                              If None is provided, the router must be a sub-route
                              (path is inherited from the controller router).
    """

    def __init__(self, path: str | None) -> None:
        """Initializes the BaseHTTPRouter instance.

        Args:
            path (Optional[str]): The path for the router, which must start with a slash ('/').
                                  If None is provided, the router must be a sub-route
                                  (path is inherited from the controller router).

        Raises:
            IncorrectPathError: If the provided path does not start with a slash.
        """
        if path is not None and not path.startswith('/'):
            raise IncorrectPathError(path=path)

        self.path = path

    @abstractmethod
    def route_register(self, application: Rapidy) -> None:
        """Registers the router with the given application.

        This is an abstract method that must be implemented by subclasses to register the
        router with an application.

        Args:
            application (Rapidy): The application in which the router should be registered.

        Raises:
            NotImplementedError: This method must be overridden by subclasses.
        """
        raise NotImplementedError


def raise_if_not_base_http_router(obj: Any) -> None:
    """Checks whether the given object is an instance of HTTPRouter.

    This check serves as an additional safeguard since mypy
    does not fully support type checking for class decorators.

    Args:
        obj: The object to check.

    Raises:
        NotBaseHTTPRouterError: If the handler is not an async function.
    """
    if not isinstance(obj, BaseHTTPRouter):
        raise RouterTypeError
