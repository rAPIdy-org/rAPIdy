from __future__ import annotations

import importlib

from rapidy_core import UNSET, Unset

from rapidy_client._content import ContentFactory, FilePart
from rapidy_client._models import (
    URL,
    AttemptListener,
    AttemptOutcome,
    AuthPolicy,
    BaseTransport,
    CallNext,
    Headers,
    Middleware,
    QueryValue,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Result,
    Timeout,
)
from rapidy_client.errors import (
    BodyTooLargeError,
    CircuitOpenError,
    ClientClosedError,
    ConnectError,
    DeadlineExceededError,
    DecodeError,
    DNSResolveError,
    HttpClientError,
    HttpTimeoutError,
    MessageValidationError,
    ProtocolError,
    ProxyError,
    RedirectError,
    RedirectNotAllowedError,
    ResponseValidationError,
    SchemaDefinitionError,
    ServerDisconnectedError,
    StatusError,
    TLSError,
    TooManyRedirectsError,
    TransportError,
    WSClosedError,
    WSError,
    WSHandshakeError,
    WSQueueFullError,
)

__all__ = (
    "UNSET",
    "URL",
    "AttemptListener",
    "AttemptOutcome",
    "AuthPolicy",
    "BaseTransport",
    "BodyTooLargeError",
    "CallNext",
    "CircuitOpenError",
    "ClientClosedError",
    "ConnectError",
    "ContentFactory",
    "DNSResolveError",
    "DeadlineExceededError",
    "DecodeError",
    "FilePart",
    "Headers",
    "HttpClientError",
    "HttpTimeoutError",
    "MessageValidationError",
    "Middleware",
    "ProtocolError",
    "ProxyError",
    "QueryValue",
    "RedirectError",
    "RedirectNotAllowedError",
    "Request",
    "RequestExtensions",
    "Response",
    "ResponseExtensions",
    "ResponseValidationError",
    "Result",
    "SchemaDefinitionError",
    "ServerDisconnectedError",
    "StatusError",
    "TLSError",
    "Timeout",
    "TooManyRedirectsError",
    "TransportError",
    "Unset",
    "WSClosedError",
    "WSError",
    "WSHandshakeError",
    "WSQueueFullError",
)

_LAZY: dict[str, str] = {}


def __getattr__(name: str) -> object:
    target = _LAZY.get(name)
    if target is not None:
        module = importlib.import_module(target)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY))
