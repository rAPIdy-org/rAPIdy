from __future__ import annotations

from importlib import import_module
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidy.testing.client import (
        AsyncTestClient,
        ClientAddress,
        create_async_test_client,
        create_test_client,
        TestClient,
    )
    from rapidy.testing.sse import AsyncSSESession, ServerSentEvent, SSESession
    from rapidy.testing.websocket import AsyncWebSocketSession, WebSocketSession

__all__ = (
    'AsyncTestClient',
    'AsyncSSESession',
    'AsyncWebSocketSession',
    'ClientAddress',
    'MissingTestingDependencyError',
    'SSESession',
    'ServerSentEvent',
    'TestClient',
    'WebSocketSession',
    'create_async_test_client',
    'create_test_client',
)

_EXPORTS = {
    'AsyncTestClient': ('rapidy.testing.client', 'AsyncTestClient'),
    'AsyncSSESession': ('rapidy.testing.sse', 'AsyncSSESession'),
    'AsyncWebSocketSession': ('rapidy.testing.websocket', 'AsyncWebSocketSession'),
    'ClientAddress': ('rapidy.testing.client', 'ClientAddress'),
    'SSESession': ('rapidy.testing.sse', 'SSESession'),
    'ServerSentEvent': ('rapidy.testing.sse', 'ServerSentEvent'),
    'TestClient': ('rapidy.testing.client', 'TestClient'),
    'WebSocketSession': ('rapidy.testing.websocket', 'WebSocketSession'),
    'create_async_test_client': ('rapidy.testing.client', 'create_async_test_client'),
    'create_test_client': ('rapidy.testing.client', 'create_test_client'),
}
_OPTIONAL_ROOTS = frozenset({'anyio', 'httpx'})


class MissingTestingDependencyError(ImportError):
    """Raised when testing helpers are used without the test extra."""

    def __init__(self) -> None:
        super().__init__("rAPIdy testing helpers require 'pip install rapidy[test]'")


def __getattr__(name: str) -> Any:
    export = _EXPORTS.get(name)
    if export is None:
        msg = f'module {__name__!r} has no attribute {name!r}'
        raise AttributeError(msg)

    module_name, attribute_name = export
    try:
        value = getattr(import_module(module_name), attribute_name)
    except ModuleNotFoundError as exc:
        missing_root = (exc.name or '').partition('.')[0]
        if missing_root in _OPTIONAL_ROOTS:
            raise MissingTestingDependencyError from exc
        raise
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted((*globals(), *_EXPORTS))
