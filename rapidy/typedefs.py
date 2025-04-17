from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Final, List, Optional, Tuple, Type, TYPE_CHECKING, Union
from typing_extensions import Literal, TypeAlias

from aiohttp.abc import AbstractView
from pydantic import BaseModel
from pydantic.fields import Deprecated
from pydantic_core import PydanticUndefined, PydanticUndefinedType

if TYPE_CHECKING:
    from rapidy.lifespan import LifespanCTX, LifespanHook  # noqa: TC004
    from rapidy.routing.http.base import BaseHTTPRouter
    from rapidy.web_request import Request
    from rapidy.web_response import StreamResponse


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
HandlerOrView: TypeAlias = Union[Handler, Type[AbstractView]]
RouterDeco: TypeAlias = Callable[[HandlerOrView], HandlerOrView]

ControllerHTTPRouterType = Any  # Not `any` of course, but `mypy` doesn't recognise the `controller` class decorator
BaseHTTPRouterType = Union['BaseHTTPRouter', ControllerHTTPRouterType]

Dataclass: TypeAlias = Any  # Not `any` of course - fix later
LocStr: TypeAlias = Union[Tuple[Union[int, str], ...], str]
ModelOrDc: TypeAlias = Type[Union[BaseModel, Dataclass]]
ResultValidate: TypeAlias = DictStrAny
ValidationErrorList: TypeAlias = List[DictStrAny]
ValidateReturn: TypeAlias = Tuple[Optional[ResultValidate], Optional[ValidationErrorList]]

# model types
NoArgAnyCallable: TypeAlias = Callable[[], Any]

Required = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType = PydanticUndefinedType
Validator = Any  # type: ignore[assignment,unused-ignore]


class ErrorWrapper(Exception):  # noqa: N818
    pass


class _Unset(Enum):
    """A sentinel enum used as placeholder."""

    UNSET = 0


Unset: Final = _Unset.UNSET
UnsetType = Literal[_Unset.UNSET]


# json
JSONEncoder = Callable[[Any], str]
JSONDecoder = Callable[[str], Any]
