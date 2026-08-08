from __future__ import annotations

from functools import partial
from typing import Any, cast, get_type_hints, Self

from rapidy.typedefs import Handler

__all__ = ('HandlerPartial',)


class HandlerPartial(partial):  # type: ignore[type-arg]
    """Bind a controller instance while retaining the original handler."""

    handler: Handler

    def __new__(cls, *, controller_instance: Any, handler: Handler) -> Self:
        """Create a partial that binds the controller instance."""
        instance = super().__new__(cls, handler, controller_instance)
        instance.handler = handler
        instance_attrs = cast('Any', instance)
        instance_attrs.__annotations__ = get_type_hints(handler, include_extras=True)
        instance_attrs.__name__ = getattr(handler, '__name__', type(handler).__name__)
        instance_attrs.__qualname__ = getattr(handler, '__qualname__', instance_attrs.__name__)
        return instance
