from __future__ import annotations

from abc import ABC

__all__ = ("RapidyException",)


class RapidyException(Exception, ABC):
    """Base exception with a stable, log-friendly text message."""

    message: str

    def __init__(self, message: str | None = None, **format_fields: str) -> None:
        message = message if message is not None else self.__class__.message
        if format_fields:
            message = message.format(**format_fields)
        super().__init__(message)
