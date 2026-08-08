from __future__ import annotations

from typing import Any

from rapidy_core.annotation_checkers import lenient_issubclass

from rapidy.request import Request
from rapidy.response import Response

__all__ = ('annotation_is_request', 'annotation_is_stream_response')


def annotation_is_request(annotation: Any) -> bool:
    """Return whether an annotation is the server Request type."""
    return lenient_issubclass(annotation, Request)


def annotation_is_stream_response(annotation: Any) -> bool:
    """Match ready-made responses until streaming types arrive in milestone 12."""
    return lenient_issubclass(annotation, Response)
