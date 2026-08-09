# WebSocket clients

`HttpClient.ws()` creates a lazy `WSConnect`. The HTTP upgrade starts when the
context is entered; leaving the context drains queued messages, sends a normal
close frame, and releases the underlying stream.

```python
async with client.ws(
    "/events",
    subprotocols=("events.v1",),
) as session:
    await session.send_text('{"action":"subscribe"}')
    message = await session.receive()
    print(session.subprotocol, message.text)
```

Both directions are bounded. The send side defaults to 256 queued frames and a
10-second wait for capacity. The receive side defaults to 256 complete messages;
when it is full, the reader stops reading the network stream until the consumer
makes room. A text or binary message may contain at most 16 MiB across all of
its fragments; exceeding `max_message_size` closes the stream and raises
`WSMessageTooLargeError`. Configure these bounds explicitly when the protocol
needs a different envelope:

```python
async with client.ws(
    "/events",
    max_message_size=2 * 1024 * 1024,
    receive_queue_limit=32,
    send_queue_limit=64,
) as session:
    ...
```

`Heartbeat()` sends a ping every 20 seconds and treats a missing pong for 20
seconds as a half-open connection. `client.aclose()` immediately closes live
sessions and wakes a pending receive with `ClientClosedError`.

Use `reconnect()` when connection setup must be repeated explicitly. Network
failures and 5xx upgrade responses are retried with capped exponential
backoff; 4xx responses and invalid handshakes are returned immediately.

```python
async for session in client.ws("/events").reconnect(max_attempts=5):
    await session.send_text('{"action":"subscribe"}')
    async for event in session.stream(Event):
        consume(event)
```

## Declarative WebSockets

`WSSocket[T]` is the simple, single-connection API. `T` can be a Pydantic model
or a discriminated union and is validated in both directions. It deliberately
has no transparent reconnect method.

```python
from rapidy_client import bind, ws
from rapidy_client.wsse import WSSocket


@ws("/events", subprotocols=("events.v1",))
async def events() -> WSSocket[Event]:
    raise NotImplementedError


socket_handle = await bind(events, client)()
async with socket_handle as socket:
    await socket.send(Event(value=1))
    echoed = await socket.receive()
```

Return `WSConnect[Send, Receive]` for separate outbound/inbound types and
explicit reconnect. Each session yielded by `reconnect()` is new, so replay
subscriptions and other setup inside the outer loop.

The WebSocket upgrade uses only middleware marked `handshake_safe=True`, plus
deadline propagation. Retry, redirects, body middleware, and authentication
policies are not applied automatically in v1; pass handshake headers through
`client.ws(..., headers=...)` when needed.
