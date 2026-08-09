from __future__ import annotations

import rapidy_core

REQUIRED_CORE_API_VERSION = 1


def ensure_core_compatibility() -> None:
    """Reject a rapidy-core installation with an incompatible public API epoch."""
    actual = getattr(rapidy_core, 'CORE_API_VERSION', None)
    if actual != REQUIRED_CORE_API_VERSION:
        message = (
            'rAPIdy 2.0 requires rapidy-core API epoch '
            f'{REQUIRED_CORE_API_VERSION}, but found {actual!r}. '
            'Install a compatible rapidy-core version (>=0.1,<0.2).'
        )
        raise ImportError(message)


ensure_core_compatibility()
