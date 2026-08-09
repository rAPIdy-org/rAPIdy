from __future__ import annotations

from collections.abc import Generator, Iterable, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import Any, cast, Self

import httpx
from anyio.from_thread import BlockingPortal, start_blocking_portal

from rapidy.application import Rapidy
from rapidy.depends import Provider
from rapidy.testing._lifespan import TestLifespan
from rapidy.testing.sse import AsyncSSESession, SSESession
from rapidy.testing.websocket import AsyncWebSocketSession, WebSocketSession
from rapidy.typedefs import ASGIScope, Receive, Send

__all__ = ('AsyncTestClient', 'TestClient', 'create_async_test_client', 'create_test_client')

type ClientAddress = tuple[str, int]


class _TestASGIApp:
    __slots__ = ('_app', '_raise_server_exceptions')

    def __init__(self, app: Rapidy, *, raise_server_exceptions: bool) -> None:
        self._app = app
        self._raise_server_exceptions = raise_server_exceptions

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        if self._raise_server_exceptions:
            scope['_rapidy_raise_server_exceptions'] = True
        await self._app(scope, receive, send)


class AsyncTestClient(httpx.AsyncClient):
    """Lifespan-aware asynchronous HTTPX client for one rAPIdy application."""

    __test__ = False

    def __init__(
        self,
        app: Rapidy,
        *,
        base_url: str = 'http://testserver',
        raise_server_exceptions: bool = True,
        root_path: str = '',
        client: ClientAddress = ('testclient', 50000),
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | None = None,
        follow_redirects: bool = True,
        di_providers: Sequence[Provider] = (),
    ) -> None:
        self.app = app
        self._client_address = client
        self._root_path = root_path
        self._test_app = _TestASGIApp(app, raise_server_exceptions=raise_server_exceptions)
        self._test_lifespan = TestLifespan(app, di_providers)
        transport = httpx.ASGITransport(
            app=cast('Any', self._test_app),
            raise_app_exceptions=raise_server_exceptions,
            root_path=root_path,
            client=client,
        )
        super().__init__(
            transport=transport,
            base_url=base_url,
            headers=headers,
            cookies=dict(cookies) if cookies is not None else None,
            follow_redirects=follow_redirects,
        )

    async def __aenter__(self) -> Self:
        await self._test_lifespan.start()
        try:
            await super().__aenter__()
        except BaseException:
            await self._test_lifespan.close()
            raise
        return self

    async def aclose(self) -> None:
        """Close HTTP resources and the application lifespan, when active."""
        try:
            await super().aclose()
        finally:
            await self._test_lifespan.close()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        """Close the client and its owned application lifespan."""
        await self.aclose()

    def websocket_connect(
        self,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        subprotocols: Sequence[str] = (),
    ) -> AsyncWebSocketSession:
        """Create an asynchronous in-process WebSocket session."""
        if not self._test_lifespan.started:
            msg = 'WebSocket tests require `async with AsyncTestClient(...)`'
            raise RuntimeError(msg)
        return AsyncWebSocketSession(
            self._test_app,
            path,
            root_path=self._root_path,
            client=self._client_address,
            headers=headers,
            subprotocols=subprotocols,
        )

    def sse_connect(
        self,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncSSESession:
        """Create an asynchronous incremental SSE session."""
        if not self._test_lifespan.started:
            msg = 'SSE tests require `async with AsyncTestClient(...)`'
            raise RuntimeError(msg)
        return AsyncSSESession(
            self._test_app,
            path,
            root_path=self._root_path,
            client=self._client_address,
            headers=headers,
        )


class _SyncASGITransport(httpx.BaseTransport):
    __slots__ = ('_async_transport', '_portal_context')

    def __init__(
        self,
        app: _TestASGIApp,
        *,
        raise_server_exceptions: bool,
        root_path: str,
        client: ClientAddress,
        portal_context: Any,
    ) -> None:
        self._async_transport = httpx.ASGITransport(
            app=cast('Any', app),
            raise_app_exceptions=raise_server_exceptions,
            root_path=root_path,
            client=client,
        )
        self._portal_context = portal_context

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        async def send_request() -> tuple[int, httpx.Headers, bytes, dict[str, Any]]:
            response = await self._async_transport.handle_async_request(request)
            try:
                content = await response.aread()
                return response.status_code, response.headers, content, response.extensions
            finally:
                await response.aclose()

        with self._portal_context() as portal:
            status_code, headers, content, extensions = portal.call(send_request)
        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=content,
            extensions=extensions,
            request=request,
        )

    def close(self) -> None:
        with self._portal_context() as portal:
            portal.call(self._async_transport.aclose)


class TestClient(httpx.Client):
    """Synchronous HTTPX client with an optional lifespan-owning context manager."""

    __test__ = False

    def __init__(
        self,
        app: Rapidy,
        *,
        base_url: str = 'http://testserver',
        raise_server_exceptions: bool = True,
        root_path: str = '',
        client: ClientAddress = ('testclient', 50000),
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | None = None,
        follow_redirects: bool = True,
        di_providers: Sequence[Provider] = (),
        backend: str = 'asyncio',
        backend_options: dict[str, Any] | None = None,
    ) -> None:
        self.app = app
        self._client_address = client
        self._root_path = root_path
        self._backend = backend
        self._backend_options = backend_options
        self._portal: BlockingPortal | None = None
        self._portal_manager: AbstractContextManager[BlockingPortal] | None = None
        self._test_lifespan = TestLifespan(app, di_providers)
        self._test_app = _TestASGIApp(app, raise_server_exceptions=raise_server_exceptions)
        transport = _SyncASGITransport(
            self._test_app,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            client=client,
            portal_context=self._portal_context,
        )
        super().__init__(
            transport=transport,
            base_url=base_url,
            headers=headers,
            cookies=dict(cookies) if cookies is not None else None,
            follow_redirects=follow_redirects,
        )

    def __enter__(self) -> Self:
        if self._portal is not None:
            msg = 'TestClient context is already entered'
            raise RuntimeError(msg)
        manager = cast(
            'AbstractContextManager[BlockingPortal]',
            start_blocking_portal(backend=self._backend, backend_options=self._backend_options),
        )
        self._portal_manager = manager
        self._portal = manager.__enter__()
        try:
            self._portal.call(self._test_lifespan.start)
            super().__enter__()
        except BaseException:
            if self._test_lifespan.started:
                self._portal.call(self._test_lifespan.close)
            self._close_portal()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            portal = self._portal
            if portal is not None:
                portal.call(self._test_lifespan.close)
            self._close_portal(exc_type, exc_value, traceback)

    def websocket_connect(
        self,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        subprotocols: Sequence[str] = (),
    ) -> WebSocketSession:
        """Create a synchronous in-process WebSocket session."""
        portal = self._portal
        if portal is None or not self._test_lifespan.started:
            msg = 'WebSocket tests require `with TestClient(...)`'
            raise RuntimeError(msg)
        async_session = AsyncWebSocketSession(
            self._test_app,
            path,
            root_path=self._root_path,
            client=self._client_address,
            headers=headers,
            subprotocols=subprotocols,
        )
        return WebSocketSession(async_session, portal)

    def sse_connect(
        self,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> SSESession:
        """Create a synchronous incremental SSE session."""
        portal = self._portal
        if portal is None or not self._test_lifespan.started:
            msg = 'SSE tests require `with TestClient(...)`'
            raise RuntimeError(msg)
        async_session = AsyncSSESession(
            self._test_app,
            path,
            root_path=self._root_path,
            client=self._client_address,
            headers=headers,
        )
        return SSESession(async_session, portal)

    @contextmanager
    def _portal_context(self) -> Generator[BlockingPortal, None, None]:
        if self._portal is not None:
            yield self._portal
            return
        with start_blocking_portal(backend=self._backend, backend_options=self._backend_options) as portal:
            yield portal

    def _close_portal(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        manager, self._portal_manager = self._portal_manager, None
        self._portal = None
        if manager is not None:
            manager.__exit__(exc_type, exc_value, traceback)


def create_test_client(
    route_handlers: Iterable[Any] = (),
    *,
    app_kwargs: Mapping[str, Any] | None = None,
    **client_kwargs: Any,
) -> TestClient:
    """Create a small application and its synchronous test client."""
    app = Rapidy(http_route_handlers=route_handlers, **dict(app_kwargs or {}))
    return TestClient(app, **client_kwargs)


def create_async_test_client(
    route_handlers: Iterable[Any] = (),
    *,
    app_kwargs: Mapping[str, Any] | None = None,
    **client_kwargs: Any,
) -> AsyncTestClient:
    """Create a small application and its asynchronous test client."""
    app = Rapidy(http_route_handlers=route_handlers, **dict(app_kwargs or {}))
    return AsyncTestClient(app, **client_kwargs)
