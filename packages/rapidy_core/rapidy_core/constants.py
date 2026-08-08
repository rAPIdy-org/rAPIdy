from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidy_core.typedefs import JSONDecoder, JSONEncoder

__all__ = ("DEFAULT_JSON_DECODER", "DEFAULT_JSON_ENCODER")

DEFAULT_JSON_ENCODER: JSONEncoder = json.dumps
DEFAULT_JSON_DECODER: JSONDecoder = json.loads
