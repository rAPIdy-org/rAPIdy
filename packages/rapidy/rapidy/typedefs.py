from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping, MutableMapping
from typing import Any, TYPE_CHECKING

from multidict import CIMultiDict
from rapidy_core.typedefs import (
    Deprecated,
    DictStrAny,
    DictStrStr,
    JSONDecoder,
    JSONEncoder,
    LocStr,
    ModelOrDc,
    NoArgAnyCallable,
    ResultValidate,
    UNSET,
    Unset as UnsetType,
    ValidateReturn,
    ValidationErrorList,
)

if TYPE_CHECKING:
    from rapidy.application import Rapidy
    from rapidy.request import Request
    from rapidy.response import Response
    from rapidy.responses.streaming import StreamResponse

__all__ = (
    'ASGIApp',
    'ASGIMessage',
    'ASGIScope',
    'CallNext',
    'ControllerHTTPRouterType',
    'Deprecated',
    'DictStrAny',
    'DictStrStr',
    'Handler',
    'HandlerOrView',
    'HTTPResponse',
    'JSONDecoder',
    'JSONEncoder',
    'LifespanCTX',
    'LifespanHook',
    'LocStr',
    'LooseHeaders',
    'Middleware',
    'ModelOrDc',
    'NoArgAnyCallable',
    'Receive',
    'ResultValidate',
    'RouterDeco',
    'Send',
    'TerminalHandler',
    'UNSET',
    'Unset',
    'UnsetType',
    'ValidateReturn',
    'ValidationErrorList',
    'View',
)

type ASGIMessage = dict[str, Any]
type ASGIScope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[ASGIMessage]]
type Send = Callable[[ASGIMessage], Awaitable[None]]
type ASGIApp = Callable[[ASGIScope, Receive, Send], Awaitable[None]]

type LooseHeader = tuple[str | bytes, str | bytes]
type LooseHeaders = Mapping[str, str] | Iterable[LooseHeader] | CIMultiDict[str]

type Handler = Callable[..., Awaitable[Any]]
type ControllerHTTPRouterType = Any
type HTTPResponse = Response | StreamResponse
type TerminalHandler = Callable[[Request], Awaitable[HTTPResponse]]
type CallNext = Callable[[Request], Awaitable[HTTPResponse]]
type Middleware = Callable[[Request, CallNext], Awaitable[HTTPResponse]]

type SyncOrAsync = Any | Awaitable[Any]
type LifespanHook = Callable[[Rapidy], SyncOrAsync] | Callable[[], SyncOrAsync]
type LifespanManager = Any
type LifespanCTX = LifespanManager | Callable[[Rapidy], LifespanManager]

Unset = UNSET


class View:
    """Base class for request-bound class handlers."""

    __slots__ = ('request',)

    def __init__(self, request: Request) -> None:
        self.request = request

    def __await__(self) -> Any:
        return self._dispatch().__await__()

    async def _dispatch(self) -> Any:
        from rapidy.exceptions import HTTPMethodNotAllowed  # noqa: PLC0415

        method_name = self.request.method.lower()
        handler = getattr(self, method_name, None)
        if handler is None:
            allowed = {
                method.upper()
                for method in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options')
                if callable(getattr(self, method, None))
            }
            raise HTTPMethodNotAllowed(self.request.method, allowed)
        return await handler()


type HandlerOrView = Handler | type[View]
type RouterDeco = Callable[[HandlerOrView], HandlerOrView]
