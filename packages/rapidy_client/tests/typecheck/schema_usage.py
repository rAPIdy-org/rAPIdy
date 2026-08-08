from __future__ import annotations

from typing import Annotated, assert_type

from rapidy_client import HttpClient, Response, bind, operation
from rapidy_client.schema import CallOptions, PathParam, controller, get, post


@get("/invoices/{invoice_id}")
async def find_invoice(
    invoice_id: Annotated[str, PathParam()],
    _options: CallOptions | None = None,
) -> Response:
    raise NotImplementedError


@controller("/billing", timeout=5.0)
class BillingApi:
    @post("/invoices/{invoice_id}")
    async def confirm(
        self,
        invoice_id: Annotated[str, PathParam()],
        _options: CallOptions | None = None,
    ) -> Response:
        raise NotImplementedError


@operation
async def invoice_status(client: HttpClient, invoice_id: str) -> int:
    response = await client.get(f"/invoices/{invoice_id}")
    return response.status


async def check(client: HttpClient) -> None:
    endpoint = bind(find_invoice, client)
    api = bind(BillingApi, client)
    status = bind(invoice_status, client)

    assert_type(await endpoint("42"), Response)
    assert_type(await api.confirm("42"), Response)
    assert_type(await status("42"), int)
