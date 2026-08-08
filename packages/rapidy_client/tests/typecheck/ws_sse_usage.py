from __future__ import annotations

from typing import Literal, assert_type

from pydantic import BaseModel
from rapidy_client import HttpClient, bind, sse, ws
from rapidy_client.wsse import SSEStream, WSConnect, WSSession, WSSocket


class Command(BaseModel):
    action: Literal["subscribe"]


class Event(BaseModel):
    value: int


@ws("/simple")
async def simple_socket() -> WSSocket[Event]:
    raise NotImplementedError


@ws("/advanced", subprotocols=("events.v1",))
async def advanced_socket() -> WSConnect[Command, Event]:
    raise NotImplementedError


@sse("/events")
async def events(*, last_event_id: str | None = None) -> SSEStream[Event]:
    raise NotImplementedError


async def check(client: HttpClient) -> None:
    simple = bind(simple_socket, client)
    advanced = bind(advanced_socket, client)
    event_stream = bind(events, client)

    simple_handle = await simple()
    assert_type(simple_handle, WSSocket[Event])
    async with simple_handle as socket:
        assert_type(await socket.receive(), Event)

    advanced_handle = await advanced()
    assert_type(advanced_handle, WSConnect[Command, Event])
    async for session in advanced_handle.reconnect(max_attempts=5):
        assert_type(session, WSSession[Command, Event])
        await session.send_model(Command(action="subscribe"))
        assert_type(await session.receive_typed(), Event)
        break

    stream_handle = await event_stream(last_event_id="checkpoint")
    assert_type(stream_handle, SSEStream[Event])
    async with stream_handle as stream:
        async for event in stream:
            assert_type(event, Event)
            break
