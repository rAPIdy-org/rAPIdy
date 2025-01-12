from functools import partial
from typing import Any

from rapidy.typedefs import Handler


class HandlerPartial(partial):  # type: ignore[type-arg]
    """Internal type for more convenient the controller handler registration."""

    def __new__(cls, *, controller_instance: Any, handler: Handler) -> 'HandlerPartial':
        """Create new `HandlerPartial`."""
        cls.handler = handler
        return super().__new__(cls, handler, controller_instance)
