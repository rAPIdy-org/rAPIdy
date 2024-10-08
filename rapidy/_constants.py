import json
from typing import Final

from aiohttp.typedefs import JSONEncoder
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_V1: Final[bool] = PYDANTIC_VERSION.startswith('1.')
PYDANTIC_V2: Final[bool] = PYDANTIC_VERSION.startswith('2.')

DEFAULT_DUMPS_ENCODER: Final[JSONEncoder] = json.dumps
