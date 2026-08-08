# Testing without network or real time

Install the testing extra to enable the public pytest plugin:

```bash
pip install "rapidy-client[testing]"
```

The plugin registers `mock_transport`, `fake_clock`, `http_client_factory`, and
`chaos_server` automatically through pytest's `pytest11` entry point. Most unit
tests only need the first three and perform no network I/O.

## Program responses and failures

Register path templates on `MockTransport`, then create a client through the
fixture-backed factory. Query parameters do not affect route matching.

```python
import pytest


@pytest.mark.asyncio
async def test_load_user(mock_transport, http_client_factory):
    mock_transport.route("GET", "/users/{id}").respond(
        status=200,
        json={"id": 42, "name": "Ada"},
    )
    client = http_client_factory("https://users.example.test")

    response = await client.get("/users/42?details=true")

    assert await response.json() == {"id": 42, "name": "Ada"}
    mock_transport.assert_called("GET", "/users/{id}", times=1)
```

Outcome chains are counted per route. The final outcome becomes the stable
response for later calls, which makes retry scenarios concise:

```python
from rapidy_client.errors import ConnectError

mock_transport.route("GET", "/flaky").times(2).raise_(
    ConnectError("temporarily unavailable")
).then().respond(status=200)
```

Every pass through the transport appears in `mock_transport.calls` as an
immutable `RecordedCall` containing the request and either its response or
exception. An unmatched request raises `MockRouteError` and lists all
registered routes.

## Advance virtual time

`fake_clock` implements the client's clock contract. Sleeping advances its
monotonic value and only yields to the event loop; it never waits for the
requested wall-clock duration.

```python
await fake_clock.sleep(30.0)
assert fake_clock.monotonic() == 30.0
```

`http_client_factory` injects the same fixture clock and mock transport into
every client it creates, then closes those clients during fixture teardown.
Externally supplied transports remain caller-owned and are not closed by the
client.

Use `chaos_server` only for transport integration tests that need real socket
behavior such as disconnects or slow bodies. It starts a fresh local
`ChaosServer` and stops it after the test.
