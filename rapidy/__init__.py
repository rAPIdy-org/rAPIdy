__version__ = '1.0.0'

from typing import Tuple, TYPE_CHECKING

from rapidy.streams import (
    DataQueue as DataQueue,
    EMPTY_PAYLOAD as EMPTY_PAYLOAD,
    EofStream as EofStream,
    FlowControlDataQueue as FlowControlDataQueue,
    StreamReader as StreamReader,
)

if TYPE_CHECKING:
    # ty aiohttp for this code <3
    # At runtime these are lazy-loaded at the bottom of the file.
    from aiohttp.worker import GunicornUVLoopWebWorker, GunicornWebWorker


__all__: Tuple[str, ...] = (
    '__version__',
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


def __getattr__(name: str) -> object:  # noqa: WPS413 WPS433
    # ty aiohttp for this code <3
    global GunicornUVLoopWebWorker, GunicornWebWorker

    # Importing gunicorn takes a long time (>100ms), so only import if actually needed.
    if name in ('GunicornUVLoopWebWorker', 'GunicornWebWorker'):  # pragma: no cover
        try:
            from aiohttp.worker import GunicornUVLoopWebWorker as guv, GunicornWebWorker as gw  # noqa: N813 WPS433
        except ImportError:
            return None

        GunicornUVLoopWebWorker = guv  # noqa: WPS442
        GunicornWebWorker = gw  # noqa: WPS442
        return guv if name == 'GunicornUVLoopWebWorker' else gw

    raise AttributeError(f'module {__name__} has no attribute {name}')
