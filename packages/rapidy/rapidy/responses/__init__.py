from typing import Any, TYPE_CHECKING

from rapidy.responses.streaming import SSEEvent, SSEResponse, StreamResponse

if TYPE_CHECKING:
    from rapidy.responses.files import FileResponse

__all__ = ('FileResponse', 'SSEEvent', 'SSEResponse', 'StreamResponse')


def __getattr__(name: str) -> Any:
    if name != 'FileResponse':
        raise AttributeError(name)
    from rapidy.responses.files import FileResponse  # noqa: PLC0415

    globals()[name] = FileResponse
    return FileResponse
