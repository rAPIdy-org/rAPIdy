from contextlib import AbstractAsyncContextManager
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Type, TYPE_CHECKING, Union

from aiohttp.abc import AbstractView
from aiohttp.typedefs import (
    Byteish,
    DEFAULT_JSON_DECODER,
    DEFAULT_JSON_ENCODER,
    JSONDecoder,
    JSONEncoder,
    LooseCookies,
    LooseCookiesIterables,
    LooseCookiesMappings,
    LooseHeaders,
    PathLike,
    RawHeaders,
    StrOrURL,
)
from typing_extensions import TypeAlias

from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.version import PY_VERSION_TUPLE
from rapidy.web_request import Request
from rapidy.web_response import StreamResponse

if TYPE_CHECKING:
    from web_app import Application

    if PY_VERSION_TUPLE < (1, 9, 0):
        AbstractAsyncContextManagerNone = AbstractAsyncContextManager
    else:
        AbstractAsyncContextManagerNone = AbstractAsyncContextManager[None]  # type: ignore[assignment, misc]


__all__ = (
    'Byteish',
    'DEFAULT_JSON_DECODER',
    'DEFAULT_JSON_ENCODER',
    'JSONEncoder',
    'JSONDecoder',
    'LooseHeaders',
    'RawHeaders',
    'StrOrURL',
    'LooseCookiesMappings',
    'LooseCookiesIterables',
    'LooseCookies',
    'Middleware',
    'CallNext',
    'Handler',
    'PathLike',
    'DictStrAny',
    'DictStrStr',
    'HandlerType',
    'SyncOrAsync',
    'CallableAsyncCTX',
    'LifespanHook',
    'LifespanCTX',
    'ValidationErrorList',
)

# support types
DictStrAny: TypeAlias = Dict[str, Any]
DictStrStr: TypeAlias = Dict[str, str]

# rapidy types
Handler: TypeAlias = Callable[..., Awaitable[Any]]
Middleware: TypeAlias = Handler
CallNext: TypeAlias = Callable[[Request], Awaitable[StreamResponse]]

# inner types
HandlerType: TypeAlias = Union[Handler, Type[AbstractView]]

# lifespan types
SyncOrAsync: TypeAlias = Union[Any, Awaitable[Any]]
LifespanHook: TypeAlias = Union[
    Callable[['Application'], SyncOrAsync],
    Callable[[], SyncOrAsync],
]

CallableAsyncCTX = Callable[['Application'], 'AbstractAsyncContextManagerNone']  # type: ignore[type-arg]  # py3.8
LifespanCTX = Union[CallableAsyncCTX, 'AbstractAsyncContextManagerNone']  # type: ignore[type-arg]  # py3.8

# validation types
ResultValidate: TypeAlias = Dict[str, Any]
ValidationErrorList: TypeAlias = List[Dict[str, Any]]
ValidateReturn: TypeAlias = Tuple[Optional[ResultValidate], Optional[ValidationErrorList]]

# model types
NoArgAnyCallable: TypeAlias = Callable[[], Any]

if PYDANTIC_V1:
    from pydantic.error_wrappers import ErrorWrapper as ErrorWrapper
    from pydantic.fields import (
        Required as Required,
        Undefined as Undefined,
        UndefinedType as UndefinedType,
        Validator as Validator,
    )

elif PYDANTIC_V2:
    from pydantic_core import PydanticUndefined, PydanticUndefinedType

    Required = PydanticUndefined
    Undefined = PydanticUndefined
    UndefinedType = PydanticUndefinedType
    Validator = Any  # type: ignore[assignment,unused-ignore]

    class ErrorWrapper(Exception):  # type: ignore[no-redef]  # noqa: N818 WPS440
        pass

else:
    raise Exception
