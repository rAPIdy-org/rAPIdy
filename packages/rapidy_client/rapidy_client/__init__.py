from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from rapidy_client._client import HttpClient
    from rapidy_client._typed import bind, operation
    from rapidy_client.config import (
        BackoffConfig,
        BreakerConfig,
        DeadlineConfig,
        HttpSettings,
        LogConfig,
        PoolLimits,
        ProxyConfig,
        RateLimitConfig,
        RedirectConfig,
        RetryConfig,
        TLSConfig,
        UpstreamConfig,
    )
    from rapidy_client.files import aiter_file, download_to, guess_extension
    from rapidy_client.schema import (
        controller,
        delete,
        get,
        head,
        options,
        patch,
        post,
        put,
    )

__all__ = (
    "UNSET",
    "URL",
    "AttemptListener",
    "AttemptOutcome",
    "AuthPolicy",
    "BackoffConfig",
    "BaseTransport",
    "BodyTooLargeError",
    "BreakerConfig",
    "CallNext",
    "CircuitOpenError",
    "ClientClosedError",
    "ConnectError",
    "ContentFactory",
    "DNSResolveError",
    "DeadlineConfig",
    "DeadlineExceededError",
    "DecodeError",
    "FilePart",
    "Headers",
    "HttpClient",
    "HttpClientError",
    "HttpSettings",
    "HttpTimeoutError",
    "LogConfig",
    "MessageValidationError",
    "Middleware",
    "PoolLimits",
    "ProtocolError",
    "ProxyConfig",
    "ProxyError",
    "QueryValue",
    "RateLimitConfig",
    "RedirectConfig",
    "RedirectError",
    "RedirectNotAllowedError",
    "Request",
    "RequestExtensions",
    "Response",
    "ResponseExtensions",
    "ResponseValidationError",
    "Result",
    "RetryConfig",
    "SchemaDefinitionError",
    "ServerDisconnectedError",
    "StatusError",
    "TLSConfig",
    "TLSError",
    "Timeout",
    "TooManyRedirectsError",
    "TransportError",
    "Unset",
    "UpstreamConfig",
    "WSClosedError",
    "WSError",
    "WSHandshakeError",
    "WSQueueFullError",
    "aiter_file",
    "bind",
    "controller",
    "delete",
    "download_to",
    "get",
    "guess_extension",
    "head",
    "operation",
    "options",
    "patch",
    "post",
    "put",
)

_LAZY: dict[str, str] = {
    "BackoffConfig": "rapidy_client.config",
    "BreakerConfig": "rapidy_client.config",
    "DeadlineConfig": "rapidy_client.config",
    "HttpClient": "rapidy_client._client",
    "HttpSettings": "rapidy_client.config",
    "LogConfig": "rapidy_client.config",
    "PoolLimits": "rapidy_client.config",
    "ProxyConfig": "rapidy_client.config",
    "RateLimitConfig": "rapidy_client.config",
    "RedirectConfig": "rapidy_client.config",
    "RetryConfig": "rapidy_client.config",
    "TLSConfig": "rapidy_client.config",
    "UpstreamConfig": "rapidy_client.config",
    "aiter_file": "rapidy_client.files",
    "bind": "rapidy_client._typed",
    "controller": "rapidy_client.schema",
    "delete": "rapidy_client.schema",
    "download_to": "rapidy_client.files",
    "get": "rapidy_client.schema",
    "guess_extension": "rapidy_client.files",
    "head": "rapidy_client.schema",
    "operation": "rapidy_client._typed",
    "options": "rapidy_client.schema",
    "patch": "rapidy_client.schema",
    "post": "rapidy_client.schema",
    "put": "rapidy_client.schema",
}


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
