from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from rapidy_core.di import (
    AsyncContainer,
    Provider,
    Scope,
    from_context,
    make_async_container,
    provide,
)

from spikes._mini.asgi_app import Send, send_response
from spikes._mini.request_proto import Request

EVENTS: list[str] = []


class MarkerDep:
    pass


class SessionMarkerDep:
    pass


class AppSingleton:
    pass


class NeedsRequest:
    def __init__(self, request: Request) -> None:
        self.request = request


class SpikeProvider(Provider):
    request = from_context(Request, scope=Scope.SESSION)

    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.APP)
    def app_singleton(self) -> AppSingleton:
        return AppSingleton()

    @provide(scope=Scope.REQUEST)
    async def marker(self) -> AsyncIterator[MarkerDep]:
        yield MarkerDep()
        self.events.append("finalizer")

    @provide(scope=Scope.REQUEST)
    def needs_request(self, request: Request) -> NeedsRequest:
        return NeedsRequest(request)

    @provide(scope=Scope.SESSION)
    async def session_marker(self) -> AsyncIterator[SessionMarkerDep]:
        yield SessionMarkerDep()
        self.events.append("session_finalizer")


class SpikeAApp:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.container: AsyncContainer = make_async_container(SpikeProvider(events))

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope["type"] != "http":
            raise RuntimeError(scope["type"])

        request = Request(scope, receive)
        if request.path == "/reset":
            self.events.clear()
            await send_response(send, 204)
            return
        if request.path == "/events":
            body = json.dumps(self.events).encode()
            await send_response(
                send, 200, body, headers=[(b"content-type", b"application/json")]
            )
            return
        if request.path != "/probe":
            await send_response(send, 404, b"not found")
            return

        async with self.container(
            context={Request: request},
            scope=Scope.REQUEST,
        ) as request_container:
            request.state.di_container = request_container
            marker = await request_container.get(MarkerDep)
            needs_request = await request_container.get(NeedsRequest)
            singleton = await request_container.get(AppSingleton)
            assert isinstance(marker, MarkerDep)
            assert needs_request.request is request
            assert isinstance(singleton, AppSingleton)
            self.events.append("handler")

            async def tracked_send(message: dict[str, Any]) -> None:
                await send(message)
                if message["type"] == "http.response.body" and not message.get(
                    "more_body", False
                ):
                    self.events.append("response_sent")

            await send_response(tracked_send, 200, b"ok")

    async def _lifespan(self, receive: Any, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await self.container.close()
                await send({"type": "lifespan.shutdown.complete"})
                return


app = SpikeAApp(EVENTS)

__all__ = (
    "AppSingleton",
    "EVENTS",
    "MarkerDep",
    "NeedsRequest",
    "SessionMarkerDep",
    "SpikeAApp",
    "SpikeProvider",
    "app",
)
