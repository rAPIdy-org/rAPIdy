from __future__ import annotations

from rapidy._core_compat import ensure_core_compatibility
from rapidy.application import Rapidy
from rapidy.serve import run_app
from rapidy.version import __version__

ensure_core_compatibility()

__all__ = ('__version__', 'Rapidy', 'run_app')
