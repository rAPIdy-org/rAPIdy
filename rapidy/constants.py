from __future__ import annotations

import json
from typing import Final, TYPE_CHECKING

from rapidy.version import PYDANTIC_VERSION_TUPLE

if TYPE_CHECKING:
    from rapidy.typedefs import JSONDecoder, JSONEncoder

CLIENT_MAX_SIZE: Final[int] = 1024**2

PYDANTIC_IS_V1: bool = PYDANTIC_VERSION_TUPLE[0] == '1'

DEFAULT_JSON_ENCODER: JSONEncoder = json.dumps
DEFAULT_JSON_DECODER: JSONDecoder = json.loads
