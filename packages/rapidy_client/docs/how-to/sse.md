# Server-Sent Events

`HttpClient.sse()` opens a normal GET stream through the complete HTTP client
pipeline. It reconnects after a network/body disconnect, remembers the latest
event `id`, and sends it as `Last-Event-ID` on the next request. A server
`retry:` field overrides the reconnect base delay when
`honor_retry_field=True`.

```python
async with client.sse("/events", last_event_id=checkpoint) as events:
    async for event in events:
        payload = event.json()
        checkpoint = event.id
```

SSE uses `total=None` and a 120-second read-idle timeout. Non-200 responses and
decode/validation failures are not reconnected automatically. Closing the
context or the parent client closes the active response and stops future
reconnects.

`ServerSentEvent` exposes `id`, `event`, `data`, and `retry` plus `.json()` and
`.as_model(Model)`. The decoder accepts CRLF, CR, and LF separators,
incremental UTF-8, a leading BOM, comments, and multiline `data:` fields.

## Declarative SSE

`SSEStream[T]` validates each `data` field through one Pydantic `TypeAdapter`,
including discriminated unions. `last_event_id` is the one reserved unmarked
keyword-only declaration argument. A call-time value overrides the decorator
default; explicit `None` clears it.

```python
from rapidy_client import bind, sse
from rapidy_client.wsse import SSEStream


@sse("/events", last_event_id="initial")
async def events(
    *,
    last_event_id: str | None = None,
) -> SSEStream[Event]:
    raise NotImplementedError


stream_handle = await bind(events, client)(last_event_id=checkpoint)
async with stream_handle as stream:
    async for event in stream:
        consume(event)
        checkpoint = stream.last_event_id
```

The default `on_invalid="raise"` produces `MessageValidationError`; choose
`on_invalid="skip"` on the decorator to log and ignore invalid events.
