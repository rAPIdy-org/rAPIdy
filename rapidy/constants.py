from typing import Final

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_V1: Final[bool] = PYDANTIC_VERSION.startswith('1.')
PYDANTIC_V2: Final[bool] = PYDANTIC_VERSION.startswith('2.')

CLIENT_MAX_SIZE: Final[int] = 1024 ** 2
MAX_BODY_SIZE: Final[int] = 1024 ** 2
