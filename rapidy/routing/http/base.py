from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from rapidy._base_exceptions import RapidyException

if TYPE_CHECKING:
    from rapidy import Rapidy


class IncorrectPathError(RapidyException):
    """IncorrectPathError."""

    message = 'Attribute `path` must start with a slash `/`, not `{path}`.'


class BaseHTTPRouter(ABC):
    """BaseHTTPRouter."""

    def __init__(self, path: Optional[str]) -> None:
        """Initialize BaseHTTPRouter."""
        if path is not None and not path.startswith('/'):
            raise IncorrectPathError(path=path)

        self.path = path

    @abstractmethod
    def route_register(self, application: 'Rapidy') -> None:
        """Abstract method for registering in an application."""
        raise NotImplementedError
