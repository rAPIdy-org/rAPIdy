from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Type, Union

from aiohttp.abc import AbstractView
from aiohttp.typedefs import (
    Byteish,
    DEFAULT_JSON_DECODER,
    DEFAULT_JSON_ENCODER,
    Handler,
    JSONDecoder,
    JSONEncoder,
    LooseCookies,
    LooseCookiesIterables,
    LooseCookiesMappings,
    LooseHeaders,
    Middleware,
    PathLike,
    RawHeaders,
    StrOrURL,
)
from typing_extensions import TypeAlias

from rapidy.constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.web_response import StreamResponse

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
    'Handler',
    'PathLike',
    'DictStrAny',
    'MethodHandler',
    'HandlerType',
    'HandlerOrMethod',
)

DictStrAny = Dict[str, Any]
MethodHandler = Callable[[], Awaitable[StreamResponse]]
HandlerType = Union[Type[AbstractView], Handler]

HandlerOrMethod = Union[Handler, MethodHandler]

ResultValidate: TypeAlias = Dict[str, Any]
ErrorList: TypeAlias = List[Dict[str, Any]]
ValidateReturn: TypeAlias = Tuple[Optional[ResultValidate], Optional[ErrorList]]


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
