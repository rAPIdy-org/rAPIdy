import enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Type, TYPE_CHECKING, Union
from typing_extensions import TypeAlias

from aiohttp.abc import AbstractView
from aiohttp.web_urldispatcher import View
from pydantic import BaseModel

from rapidy.constants import PYDANTIC_IS_V1
from rapidy.routing.http.base import BaseHTTPRouter

if TYPE_CHECKING:
    from rapidy.lifespan import LifespanCTX, LifespanHook  # noqa: TC004
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
RouterDeco = Callable[[HandlerOrView], HandlerOrView]
HTTPRouterType = Union[
    BaseHTTPRouter,
    Type[View],  # mypy is bullshit - class decorators that change type don't work
]

# validation types
LocStr = Union[Tuple[Union[int, str], ...], str]
ModelOrDc = Type[Union[BaseModel, 'Dataclass']]
ResultValidate = DictStrAny
ValidationErrorList: TypeAlias = List[DictStrAny]
ValidateReturn: TypeAlias = Tuple[Optional[ResultValidate], Optional[ValidationErrorList]]

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


Unset = enum.Enum('Unset', 'unset').unset  # type: ignore[attr-defined]

# json
JSONEncoder = Callable[[Any], str]
JSONDecoder = Callable[[str], Any]
