from __future__ import annotations

from typing import Any

from rapidy.response import Response

__all__ = ('ensure_response',)


def ensure_response(value: Any) -> Response:
    """Normalize the milestone-02 terminal result."""
    return value if isinstance(value, Response) else Response(value)
