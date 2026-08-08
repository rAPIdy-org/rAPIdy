from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).parents[2]
_PACKAGE_ROOT_STR = str(_PACKAGE_ROOT)
if _PACKAGE_ROOT_STR in sys.path:
    sys.path.remove(_PACKAGE_ROOT_STR)
sys.path.insert(0, _PACKAGE_ROOT_STR)
