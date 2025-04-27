__version__ = '1.1.1'

from typing import Tuple, TYPE_CHECKING

from aiohttp.web import run_app

from rapidy.streams import DataQueue, EMPTY_PAYLOAD, EofStream, FlowControlDataQueue, StreamReader
from rapidy.web_app import Application as Rapidy

if TYPE_CHECKING:
    # ty aiohttp for this code <3
    # At runtime these are lazy-loaded at the bottom of the file.
    from aiohttp.worker import GunicornUVLoopWebWorker, GunicornWebWorker  # noqa: TC004


__all__: Tuple[str, ...] = (
    '__version__',
    # Application
    'Rapidy',
    'run_app',
    # streams
    'DataQueue',
    'EMPTY_PAYLOAD',
    'EofStream',
    'FlowControlDataQueue',
    'StreamReader',
    # workers (imported lazily with __getattr__)
    'GunicornUVLoopWebWorker',
    'GunicornWebWorker',
)


def __getattr__(name: str) -> object:
    # ty aiohttp for this code <3
    global GunicornUVLoopWebWorker, GunicornWebWorker  # noqa: PLW0603

    # Importing gunicorn takes a long time (>100ms), so only import if actually needed.
    if name in ('GunicornUVLoopWebWorker', 'GunicornWebWorker'):  # pragma: no cover
        try:
            from aiohttp.worker import (
                GunicornUVLoopWebWorker as guv,  # noqa: N813
                GunicornWebWorker as gw,  # noqa: N813
            )
        except ImportError:
            return None

        GunicornUVLoopWebWorker = guv
        GunicornWebWorker = gw
        return guv if name == 'GunicornUVLoopWebWorker' else gw

    raise AttributeError(f'module {__name__} has no attribute {name}')  # noqa: EM102 TRY003
