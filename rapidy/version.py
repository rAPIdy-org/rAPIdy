from __future__ import annotations

import platform
from typing import Tuple

from aiohttp import __version__ as __aiohttp__version__
from pydantic.version import VERSION as PYDANTIC_STR_VERSION

from rapidy import __version__ as __rapidy__version__


def parse_version(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.partition('+')[0].split('.')))


PY_VERSION = platform.python_version()
PY_VERSION_TUPLE = tuple(int(num) for num in platform.python_version_tuple())
AIOHTTP_VERSION_TUPLE: Tuple[int, ...] = parse_version(__aiohttp__version__)
PYDANTIC_VERSION_TUPLE: Tuple[int | str, ...] = tuple(PYDANTIC_STR_VERSION.split('.'))

SERVER_INFO: str = 'Python/{} rapidy/{} pydantic/{} aiohttp/{}'.format(  # noqa: UP032
    PY_VERSION,
    __rapidy__version__,
    PYDANTIC_STR_VERSION,
    __aiohttp__version__,
)
