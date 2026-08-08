from __future__ import annotations

from typing import Final

from rapidy_core.constants import DEFAULT_JSON_DECODER, DEFAULT_JSON_ENCODER

__all__ = ('CLIENT_MAX_SIZE', 'DEFAULT_JSON_DECODER', 'DEFAULT_JSON_ENCODER')

CLIENT_MAX_SIZE: Final = 1024**2
