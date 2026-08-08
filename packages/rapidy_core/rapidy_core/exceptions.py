from __future__ import annotations

from abc import ABC
from typing import Final

__all__ = ("RapidyException",)

BORDER_LEN: Final[int] = 30


class RapidyException(Exception, ABC):
    """Base exception with the message framing used by rAPIdy."""

    border = "\n" + "-" * BORDER_LEN + "\n"
    message: str

    def __init__(self, message: str | None = None, **format_fields: str) -> None:
        message = message if message is not None else self.__class__.message
        if format_fields:
            message = message.format(**format_fields)
        super().__init__(self._wrap_message(message))

    @staticmethod
    def _wrap_message(message: str) -> str:
        return RapidyException.border + message + RapidyException.border
