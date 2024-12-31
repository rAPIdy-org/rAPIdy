from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidy.web_app import Application


class BaseHTTPRouter(ABC):
    def __init__(self, path: str) -> None:
        if not path.startswith('/'):
            raise ValueError(f'Path `{path}` must start with a slash - `/`.')
        self.path = path

    @abstractmethod
    def register(self, application: 'Application') -> None:
        raise NotImplementedError
