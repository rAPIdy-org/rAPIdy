import json
from typing import Final, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidy.typedefs import JSONDecoder, JSONEncoder

CLIENT_MAX_SIZE: Final[int] = 1024**2

DEFAULT_JSON_ENCODER: 'JSONEncoder' = json.dumps
DEFAULT_JSON_DECODER: 'JSONDecoder' = json.loads
