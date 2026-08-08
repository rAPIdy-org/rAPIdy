from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).parents[2]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))
