from enum import Enum
from typing import Final

DEFAULT_RETURN_TYPE: type[str] = str
DEFAULT_RETURN_VALUE: Final[str] = 'test'


class ClientBodyExtractMethod(str, Enum):  # noqa: UP042 - preserve the rAPIdy 1.x public test enum.
    text = 'text'
    read = 'read'
    json = 'json'
