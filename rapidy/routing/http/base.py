from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from rapidy._base_exceptions import RapidyException

if TYPE_CHECKING:
    from rapidy import Rapidy


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

    def __init__(self, path: Optional[str]) -> None:
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
    def route_register(self, application: 'Rapidy') -> None:
        """Registers the router with the given application.

        This is an abstract method that must be implemented by subclasses to register the
        router with an application.

        Args:
            application (Rapidy): The application in which the router should be registered.

        Raises:
            NotImplementedError: This method must be overridden by subclasses.
        """
        raise NotImplementedError
