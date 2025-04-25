from __future__ import annotations

from abc import ABC
from typing import Any, Final

from rapidy.routing.http.helper_types import HandlerPartial

BORDER_LEN: Final[int] = 30


class RapidyException(Exception, ABC):  # noqa: N818
    """Base class for exceptions in the Rapidy framework.

    This exception is the base class for all exceptions in the Rapidy framework.
    It provides a customizable message format and ensures that the message is wrapped with borders.

    Attributes:
        border (str): A string that defines the border used to wrap the exception message.
        message (str): The message to be displayed when the exception is raised.
    """

    border = '\n' + '-' * BORDER_LEN + '\n'
    message: str

    def __init__(self, message: str | None = None, **format_fields: str) -> None:
        """Initialize a RapidyException instance.

        Args:
            message (Optional[str]): The message to display. If not provided, uses the default
                                     message defined in the class.
            format_fields (str): Additional fields to format the message with.

        Raises:
            ValueError: If the message cannot be formatted with the provided fields.
        """
        message = message if message is not None else self.__class__.message

        if format_fields:
            message = message.format(**format_fields)

        super().__init__(self._wrap_message(message))

    @staticmethod
    def _wrap_message(message: str) -> str:
        """Wrap the message with borders for display.

        Args:
            message (str): The message to be wrapped.

        Returns:
            str: The message wrapped with borders.
        """
        return RapidyException.border + message + RapidyException.border


class RapidyHandlerException(RapidyException, ABC):
    """Exception raised for errors related to handlers in the Rapidy framework.

    This exception is specifically used when there is an issue with a handler, such as
    missing or incorrect attributes.

    Methods:
        create: Creates an instance of RapidyHandlerException with detailed information about
                the handler and associated attributes.
    """

    @classmethod
    def create(
        cls,
        *,
        handler: Any,
        attr_name: str | None = None,
        **format_fields: str,
    ) -> RapidyHandlerException:
        """Create a new RapidyHandlerException with detailed handler information.

        Args:
            handler (Any): The handler causing the exception. If the handler is a HandlerPartial,
                           the actual handler function is extracted.
            attr_name (Optional[str]): The name of the attribute associated with the handler.
            format_fields (str): Additional fields to format the message with.

        Returns:
            RapidyHandlerException: A new instance of RapidyHandlerException with the formatted message.
        """
        if isinstance(handler, HandlerPartial):
            handler = handler.handler

        msg = f'{cls.message}\nHandler path: `{handler.__code__.co_filename}`\nHandler name: `{handler.__name__}`'
        if attr_name:
            msg = f'{msg}\nAttribute name: `{attr_name}`'
        return cls(msg, **format_fields)
