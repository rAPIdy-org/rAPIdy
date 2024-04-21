import platform
from typing import Tuple

from aiohttp import __version__ as __aiohttp__version__  # noqa: WPS116

from rapidy import __version__ as __rapidy__version__  # noqa: WPS116


def parse_version(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.partition('+')[0].split('.')))  # noqa: WPS221


PY_VERSION = platform.python_version()
PY_VERSION_TUPLE = tuple(int(num) for num in platform.python_version_tuple())
AIOHTTP_VERSION_TUPLE = parse_version(__aiohttp__version__)

SERVER_INFO: str = 'Python/{} rapidy/{} aiohttp/{}'.format(PY_VERSION, __rapidy__version__, __aiohttp__version__)
