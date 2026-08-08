from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field
from rapidy_client import (
    BackoffConfig,
    ClientClosedError,
    DecodeError,
    Headers,
    HttpClient,
    MessageValidationError,
    Request,
    Response,
    ResponseExtensions,
    SSEReconnect,
    SSEStream,
    UpstreamConfig,
    bind,
    sse,
)
from rapidy_client.sse import ServerSentEvent, SSEDecoder


async def _chunks(*values: bytes) -> AsyncIterator[bytes]:
    for value in values:
        yield value


async def _decode(*values: bytes) -> list[ServerSentEvent]:
    return [event async for event in SSEDecoder().iter_bytes(_chunks(*values))]


@pytest.mark.asyncio
async def test_decoder_handles_boundaries_bom_and_multiline_data() -> None:
    encoded = "\ufeffid: 42\rdata: привет\r\ndata: world\nretry: 3000\n\n".encode()
    split = encoded.index("в".encode()) + 1

    events = await _decode(encoded[:split], encoded[split:])

    assert events == [
        ServerSentEvent(
            id="42",
            event=None,
            data="привет\nworld",
            retry=3000,
        )
    ]


@pytest.mark.asyncio
async def test_decoder_ignores_comments_and_persists_id() -> None:
    events = await _decode(b": ping\nid: 5\ndata: one\n\ndata: two\n\n")
    assert [event.data for event in events] == ["one", "two"]
    assert [event.id for event in events] == ["5", "5"]


def test_event_json_and_model_errors() -> None:
    assert ServerSentEvent(data='{"value": 1}').json() == {"value": 1}
    with pytest.raises(DecodeError):
        ServerSentEvent(data="{").json()

    class Event(BaseModel):
        value: int

    assert ServerSentEvent(data='{"value": 1}').as_model(Event) == Event(value=1)
    with pytest.raises(MessageValidationError):
        ServerSentEvent(data='{"value": "bad"}').as_model(Event)


class Added(BaseModel):
    kind: Literal["added"]
    value: int


class Removed(BaseModel):
    kind: Literal["removed"]
    value: int


Event = Annotated[Added | Removed, Field(discriminator="kind")]


@sse("/events", last_event_id="decorator")
async def events(*, last_event_id: str | None = None) -> SSEStream[Event]:
    pass


class _SSETransport:
    def __init__(self) -> None:
        self.requests: list[Request] = []

    async def handle(self, request: Request) -> Response:
        self.requests.append(request)
        body = b'id: next\ndata: {"kind":"added","value":7}\n\n'
        return Response(
            status=200,
            headers=Headers({"Content-Type": "text/event-stream"}),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=1),
            stream=_chunks(body),
        )

    async def aclose(self) -> None:
        return None


def _client(transport: _SSETransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig(base_url="https://example.test"),
        transport=transport,
    )


@pytest.mark.asyncio
async def test_declarative_sse_union_and_checkpoint_override() -> None:
    transport = _SSETransport()
    endpoint = bind(events, _client(transport))

    async with await endpoint(last_event_id=None) as stream:
        assert await anext(stream) == Added(kind="added", value=7)
        assert stream.last_event_id == "next"

    assert "Last-Event-ID" not in transport.requests[0].headers


@pytest.mark.asyncio
async def test_sse_call_uses_decorator_checkpoint_when_omitted() -> None:
    transport = _SSETransport()
    endpoint = bind(events, _client(transport))

    async with await endpoint() as stream:
        await anext(stream)

    assert transport.requests[0].headers["Last-Event-ID"] == "decorator"


@pytest.mark.asyncio
async def test_imperative_sse_reconnects_with_last_event_id() -> None:
    transport = _SSETransport()
    client = _client(transport)
    connection = client.sse(
        "/events",
        reconnect=SSEReconnect(
            backoff=BackoffConfig(base=0.0, cap=0.0, jitter="none"),
            max_attempts=2,
        ),
    )

    async with connection as stream:
        assert (await anext(stream)).id == "next"
        assert (await anext(stream)).id == "next"

    assert len(transport.requests) == 2
    assert transport.requests[1].headers["Last-Event-ID"] == "next"


@pytest.mark.asyncio
async def test_client_close_wakes_active_sse_consumer() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocking_body() -> AsyncIterator[bytes]:
        started.set()
        await release.wait()
        yield b"data: never\n\n"

    class BlockingTransport(_SSETransport):
        async def handle(self, request: Request) -> Response:
            self.requests.append(request)
            return Response(
                status=200,
                headers=Headers({"Content-Type": "text/event-stream"}),
                request=request,
                extensions=ResponseExtensions(elapsed=0.0, attempt=1),
                stream=blocking_body(),
            )

    client = _client(BlockingTransport())
    connection = client.sse("/events")
    stream = await connection.__aenter__()
    receive = asyncio.create_task(anext(stream))
    await started.wait()

    await client.aclose()

    with pytest.raises(ClientClosedError):
        await receive
