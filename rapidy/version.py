import platform
from typing import Tuple, Union

from aiohttp import __version__ as __aiohttp__version__  # noqa: WPS116
from pydantic.version import VERSION as PYDANTIC_STR_VERSION

from rapidy import __version__ as __rapidy__version__  # noqa: WPS116


def parse_version(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.partition('+')[0].split('.')))  # noqa: WPS221


PY_VERSION = platform.python_version()
PY_VERSION_TUPLE = tuple(int(num) for num in platform.python_version_tuple())
AIOHTTP_VERSION_TUPLE: Tuple[int, ...] = parse_version(__aiohttp__version__)
PYDANTIC_VERSION_TUPLE: Tuple[Union[int, str], ...] = tuple(PYDANTIC_STR_VERSION.split('.'))

SERVER_INFO: str = 'Python/{} rapidy/{} pydantic/{} aiohttp/{}'.format(
    PY_VERSION,
    __rapidy__version__,
    PYDANTIC_STR_VERSION,
    __aiohttp__version__,
)
