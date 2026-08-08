from __future__ import annotations

from typing import Any

from rapidy_core.exceptions import RapidyException

__all__ = ('RapidyException', 'RapidyHandlerException')


class RapidyHandlerException(RapidyException):
    """Server-specific handler error built on the shared core exception."""

    @classmethod
    def create(
        cls,
        *,
        handler: Any,
        attr_name: str | None = None,
        **format_fields: str,
    ) -> RapidyHandlerException:
        """Attach stable source details to a handler-related error."""
        source_handler = getattr(handler, 'handler', handler)
        code = getattr(source_handler, '__code__', None)
        source_path = getattr(code, 'co_filename', '<unknown>')
        handler_name = getattr(source_handler, '__name__', type(source_handler).__name__)
        message = f'{cls.message}\nHandler path: `{source_path}`\nHandler name: `{handler_name}`'
        if attr_name:
            message = f'{message}\nAttribute name: `{attr_name}`'
        return cls(message, **format_fields)
