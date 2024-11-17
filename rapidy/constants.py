import json

from rapidy.version import PYDANTIC_VERSION_TUPLE

PYDANTIC_IS_V1 = PYDANTIC_VERSION_TUPLE[0] == '1'

DEFAULT_JSON_ENCODER = json.dumps
DEFAULT_JSON_DECODER = json.loads
