from __future__ import annotations

from functools import partial
from typing import Any
from typing_extensions import Self

from rapidy.typedefs import Handler


class HandlerPartial(partial):  # type: ignore[type-arg]
    """An internal type for more convenient controller handler registration.

    This class is used to create partial functions with additional metadata, such as the handler
    and the controller instance, to streamline the registration of handler functions.
    """

    def __new__(cls, *, controller_instance: Any, handler: Handler) -> Self:
        """Create a new `HandlerPartial`.

        Args:
            controller_instance (Any): The instance of the controller.
            handler (Handler): The handler function associated with the controller.

        Returns:
            HandlerPartial: A new instance of `HandlerPartial`.
        """
        cls.handler = handler
        return super().__new__(cls, handler, controller_instance)
