# Declarative HTTP schema

`rapidy-client` can describe an HTTP call once and bind that declaration to a
specific `HttpClient`. Binding is explicit: declarations do not contain an
upstream name and can be reused with independent clients.

```python
from typing import Annotated

from rapidy_client import HttpClient, Response, bind
from rapidy_client.schema import PathParam, QueryParam, get


@get("/invoices/{invoice_id}")
async def find_invoice(
    invoice_id: Annotated[str, PathParam()],
    archived: Annotated[bool, QueryParam()] = False,
) -> Response:
    raise NotImplementedError


endpoint = bind(find_invoice, client)
response = await endpoint("inv-42", archived=False)
```

The default-value marker form is equivalent:

```python
@get("/invoices/{invoice_id}")
async def find_invoice(invoice_id: str = PathParam()) -> Response:
    raise NotImplementedError
```

Controllers add a shared path prefix and inherited call settings. Method
settings override controller settings; middleware is concatenated in
controller-to-method order.

```python
from rapidy_client.schema import CallOptions, controller, post


@controller("/billing", timeout=5.0)
class BillingApi:
    @post("/invoices/{invoice_id}", timeout=15.0)
    async def confirm(
        self,
        invoice_id: Annotated[str, PathParam()],
    ) -> Response:
        raise NotImplementedError


api = bind(BillingApi, client)
response = await api.confirm(
    "inv-42",
    _options=CallOptions(timeout=30.0),
)
```

`CallOptions` is the strongest per-call override. `@operation` covers calls
whose body contains real orchestration logic: it accepts only a free async
function with a leading `HttpClient`, and `bind` hides and injects that first
argument.

Schema errors are raised while decorating or binding, before network I/O.
Endpoint declaration bodies may contain only `pass`, `...`, a docstring, or
`raise NotImplementedError`.

## Typed responses and declared statuses

A pydantic return annotation parses a successful JSON response. A status in
`statuses` becomes a typed value rather than an exception; every other non-2xx
response still raises `StatusError`.

```python
from pydantic import BaseModel

from rapidy_client import Result


class Invoice(BaseModel):
    invoice_id: str


@get("/invoices/{invoice_id}", statuses={404: None})
async def maybe_invoice(
    invoice_id: Annotated[str, PathParam()],
) -> Result[Invoice | None]:
    raise NotImplementedError
```

`Result[T]` preserves the exact response status and headers next to the typed
value. Unexpected errors never enter `Result`; use `error_model=` when a
`StatusError` should carry a parsed error body. `Response` is the explicit raw
escape hatch and is fully buffered before it is returned.

Request models honor `request_by_alias`, `request_include_fields`,
`request_exclude_fields`, `request_exclude_unset`,
`request_exclude_defaults`, and `request_exclude_none`. Query lists repeat by
default; choose `QuerySerialization(list_style=ListStyle.CSV)` on a declaration
when the upstream expects comma-separated values.
