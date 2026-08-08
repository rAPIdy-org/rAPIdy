from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from typing import Any, TYPE_CHECKING

from rapidy_core.typedefs import JSONDecoder, JSONEncoder, UNSET, Unset

if TYPE_CHECKING:
    from rapidy.application import Rapidy
    from rapidy.request import Request
    from rapidy.response import Response

__all__ = (
    'ASGIApp',
    'ASGIMessage',
    'ASGIScope',
    'CallNext',
    'Handler',
    'JSONDecoder',
    'JSONEncoder',
    'LifespanCTX',
    'LifespanHook',
    'LooseHeaders',
    'Middleware',
    'Receive',
    'Send',
    'UNSET',
    'Unset',
    'View',
)

type ASGIMessage = dict[str, Any]
type ASGIScope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[ASGIMessage]]
type Send = Callable[[ASGIMessage], Awaitable[None]]
type ASGIApp = Callable[[ASGIScope, Receive, Send], Awaitable[None]]

type LooseHeader = tuple[str | bytes, str | bytes]
type LooseHeaders = Mapping[str, str] | Sequence[LooseHeader]

type Handler = Callable[..., Awaitable[Any]]
type View = Handler
type CallNext = Callable[[Request], Awaitable[Response]]
type Middleware = Callable[[Request, CallNext], Awaitable[Response]]

type SyncOrAsync = Any | Awaitable[Any]
type LifespanHook = Callable[[Rapidy], SyncOrAsync] | Callable[[], SyncOrAsync]
type LifespanManager = Any
type LifespanCTX = LifespanManager | Callable[[Rapidy], LifespanManager]
