from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidy.web_app import Application


class BaseHTTPRouter(ABC):
    """BaseHTTPRouter."""

    def __init__(self, path: str) -> None:
        """Initialize BaseHTTPRouter."""
        if not path.startswith('/'):
            raise ValueError(f'Path `{path}` must start with a slash - `/`.')  # noqa: EM102 TRY003
        self.path = path

    @abstractmethod
    def register(self, application: 'Application') -> None:
        """Abstract method for registering in an application."""
        raise NotImplementedError
