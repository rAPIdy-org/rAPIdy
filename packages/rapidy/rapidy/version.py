from __future__ import annotations

import platform

from pydantic.version import VERSION as PYDANTIC_VERSION

__all__ = (
    'PYDANTIC_VERSION_TUPLE',
    'PY_VERSION',
    'PY_VERSION_TUPLE',
    'SERVER_INFO',
    '__version__',
)

__version__ = '2.0.0'

PY_VERSION = platform.python_version()
PY_VERSION_TUPLE = tuple(int(component) for component in platform.python_version_tuple())
PYDANTIC_VERSION_TUPLE = tuple(PYDANTIC_VERSION.split('.'))

SERVER_INFO = f'Rapidy/{__version__} Python/{PY_VERSION_TUPLE[0]}.{PY_VERSION_TUPLE[1]}'
