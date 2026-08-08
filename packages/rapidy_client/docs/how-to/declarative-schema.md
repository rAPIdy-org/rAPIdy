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
