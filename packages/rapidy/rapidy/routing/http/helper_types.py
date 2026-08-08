from __future__ import annotations

from functools import partial
from typing import Any, Self

from rapidy.typedefs import Handler

__all__ = ('HandlerPartial',)


class HandlerPartial(partial):  # type: ignore[type-arg]
    """Bind a controller instance while retaining the original handler."""

    handler: Handler

    def __new__(cls, *, controller_instance: Any, handler: Handler) -> Self:
        """Create a partial that binds the controller instance."""
        cls.handler = handler
        return super().__new__(cls, handler, controller_instance)
