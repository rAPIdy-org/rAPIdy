from abc import ABC
from typing import Any, Final, Optional

BORDER_LEN: Final[int] = 30


class RapidyException(Exception, ABC):  # noqa: N818
    border = '\n' + '-' * BORDER_LEN + '\n'
    message: str

    def __init__(self, message: Optional[str] = None, **format_fields: str) -> None:
        message = message if message is not None else self.__class__.message

        if format_fields:
            message = message.format(**format_fields)

        super().__init__(self._wrap_message(message))

    @staticmethod
    def _wrap_message(message: str) -> str:
        return RapidyException.border + message + RapidyException.border


class RapidyHandlerException(RapidyException, ABC):
    @classmethod
    def create(
        cls,
        *,
        handler: Any,
        attr_name: Optional[str] = None,
        **format_fields: str,
    ) -> 'RapidyHandlerException':
        msg = f'{cls.message}\nHandler path: `{handler.__code__.co_filename}`\nHandler name: `{handler.__name__}`'
        if attr_name:
            msg = f'{msg}\nAttribute name: `{attr_name}`'
        return cls(msg, **format_fields)
