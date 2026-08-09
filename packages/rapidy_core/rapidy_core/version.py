from __future__ import annotations

__all__ = ("CORE_API_VERSION", "__version__")

# Increment this epoch whenever a consumer-visible rapidy_core contract changes
# incompatibly. Consumer packages validate it during their root import.
CORE_API_VERSION = 1
__version__ = "0.1.0"
