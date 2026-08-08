from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Final, List, Tuple, Type, TYPE_CHECKING, Union
from typing_extensions import Literal, TypeAlias

from aiohttp.abc import AbstractView
from pydantic import BaseModel

from rapidy.constants import PYDANTIC_IS_V1

if TYPE_CHECKING:
    from rapidy.lifespan import LifespanCTX, LifespanHook  # noqa: TC004
    from rapidy.routing.http.base import BaseHTTPRouter
    from rapidy.web_request import Request
    from rapidy.web_response import StreamResponse

    if PYDANTIC_IS_V1:
        from pydantic.dataclasses import Dataclass


__all__ = (
    'Deprecated',
    'Middleware',
    'CallNext',
    'Handler',
    'DictStrAny',
    'DictStrStr',
    'NoArgAnyCallable',
    'HandlerOrView',
    'LifespanCTX',
    'LifespanHook',
    'ResultValidate',
    'ValidationErrorList',
    'ValidateReturn',
    'JSONEncoder',
    'JSONDecoder',
    'Unset',
    'UnsetType',
)

# support types
DictStrAny: TypeAlias = Dict[str, Any]
DictStrStr: TypeAlias = Dict[str, str]

# rapidy types
Handler: TypeAlias = Callable[..., Awaitable[Any]]
Middleware: TypeAlias = Handler
CallNext: TypeAlias = Callable[['Request'], Awaitable['StreamResponse']]

# inner types
HandlerOrView: TypeAlias = Handler | Type[AbstractView]
RouterDeco = Callable[[HandlerOrView], HandlerOrView]

ControllerHTTPRouterType = Any  # Not `any` of course, but `mypy` doesn't recognise the `controller` class decorator
BaseHTTPRouterType = Union['BaseHTTPRouter', ControllerHTTPRouterType]

# validation types
LocStr = Tuple[int | str, ...] | str
ModelOrDc = Type[Union[BaseModel, 'Dataclass']]
ResultValidate = DictStrAny
ValidationErrorList: TypeAlias = List[DictStrAny]
ValidateReturn: TypeAlias = Tuple[ResultValidate | None, ValidationErrorList | None]

# model types
NoArgAnyCallable: TypeAlias = Callable[[], Any]

if PYDANTIC_IS_V1:
    from typing_extensions import deprecated as Deprecated  # noqa: N812

    from pydantic.error_wrappers import ErrorWrapper
    from pydantic.fields import Required, Undefined, UndefinedType, Validator

else:
    from pydantic.fields import Deprecated  # type: ignore[no-redef]
    from pydantic_core import PydanticUndefined, PydanticUndefinedType

    Required = PydanticUndefined
    Undefined = PydanticUndefined
    UndefinedType = PydanticUndefinedType
    Validator = Any  # type: ignore[assignment,unused-ignore]

    class ErrorWrapper(Exception):  # type: ignore[no-redef]  # noqa: N818
        pass


class _Unset(Enum):
    """A sentinel enum used as placeholder."""

    UNSET = 0


Unset: Final = _Unset.UNSET
UnsetType = Literal[_Unset.UNSET]


# json
JSONEncoder = Callable[[Any], str]
JSONDecoder = Callable[[str], Any]
