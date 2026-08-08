# rapidy-client

`rapidy-client` is the standalone, typed async HTTP client for the rAPIdy
family. It supports imperative and declarative HTTP calls, streaming,
WebSockets, SSE, retries, deadlines, observability, and component-qualified
dependency injection.

The package targets Python 3.13 and 3.14 and ships a `py.typed` marker.

## Installation

```shell
pip install rapidy-client
```

Optional compression and HTTP/2 support are available as extras:

```shell
pip install "rapidy-client[brotli,http2]"
```

## Imperative client

```python
from rapidy_client import HttpClient, UpstreamConfig


async def load_invoice(invoice_id: int) -> dict[str, object]:
    config = UpstreamConfig(base_url="https://billing.example")
    client = HttpClient(config, name="billing")
    try:
        response = await client.get(
            "/invoices/{invoice_id}",
            path_params={"invoice_id": invoice_id},
            deadline=5.0,
        )
        return await response.json()
    finally:
        await client.aclose()
```

## Declarative client

Declarations are environment-free and bind explicitly to a client:

```python
from typing import Annotated

from pydantic import BaseModel
from rapidy_client import HttpClient, UpstreamConfig, bind, get
from rapidy_client.schema import PathParam


class Invoice(BaseModel):
    id: int
    amount: int


@get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: Annotated[int, PathParam()],
) -> Invoice:
    raise NotImplementedError


async def load_typed_invoice(invoice_id: int) -> Invoice:
    client = HttpClient(
        UpstreamConfig(base_url="https://billing.example"),
        name="billing",
    )
    try:
        endpoint = bind(get_invoice, client)
        return await endpoint(invoice_id)
    finally:
        await client.aclose()
```

The return annotation controls response parsing and validation. Use `Result[T]`
when the caller also needs the response status and headers.

## Dependency injection

`HttpApp` creates one application-scoped client per `rapidy-core` component and
owns its lifecycle:

```python
from rapidy_client import HttpClient, UpstreamConfig
from rapidy_client.di import HttpApp
from rapidy_core.di import Component

BILLING = Component("billing")
AUDIT = Component("audit")

app = HttpApp(
    upstreams={
        BILLING: UpstreamConfig(base_url="https://billing.example"),
        AUDIT: UpstreamConfig(base_url="https://audit.example"),
    }
)


async def use_components() -> None:
    async with app:
        billing = await app.container.get(HttpClient, component=BILLING)
        await billing.get("/health")
```

## Protocols and streaming

- `client.stream(...)` consumes response bodies without buffering them.
- `client.ws(...)` provides bounded concurrent sends and a single receive
  consumer.
- `client.sse(...)` parses events and supports checkpoint reconnects.
- Declarative `@ws` and `@sse` endpoints apply typed message validation.

## Documentation

Task-focused guides live in [`docs/how-to`](docs/how-to), including
configuration, middleware, retry/deadline behavior, testing, DI, files,
WebSockets, and SSE.

The accepted architecture is recorded in
[`docs/adr/http-client-redesign.md`](docs/adr/http-client-redesign.md), and
release notes are in [`CHANGELOG.md`](CHANGELOG.md).
