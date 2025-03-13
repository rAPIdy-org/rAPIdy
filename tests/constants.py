from enum import Enum
from typing import Final, Type

DEFAULT_RETURN_TYPE: Type[str] = str
DEFAULT_RETURN_VALUE: Final[str] = 'test'


class ClientBodyExtractMethod(str, Enum):
    text = 'text'
    read = 'read'
    json = 'json'
