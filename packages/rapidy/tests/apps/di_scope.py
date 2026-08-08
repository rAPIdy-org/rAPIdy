from __future__ import annotations

from collections.abc import AsyncIterator

from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get, Response
from rapidy.typedefs import Send

EVENTS: list[str] = []


class RequestResource:
    pass


class ScopeProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def resource(self) -> AsyncIterator[RequestResource]:
        yield RequestResource()
        EVENTS.append('finalizer')


class TrackedResponse(Response):
    async def _send(self, send: Send, *, server_info: str | None = None) -> None:
        await super()._send(send, server_info=server_info)
        EVENTS.append('response_sent')


@get('/probe')
async def probe(resource: FromDI[RequestResource]) -> Response:
    assert resource is not None
    EVENTS.append('handler')
    return TrackedResponse('ok')


@get('/events')
async def events() -> str:
    return ','.join(EVENTS)


app = Rapidy(di_providers=[ScopeProvider()], http_route_handlers=[probe, events])
