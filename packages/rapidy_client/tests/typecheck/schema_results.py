from __future__ import annotations

from typing import Annotated, assert_type

from pydantic import BaseModel
from rapidy_client import HttpClient, Result, bind
from rapidy_client.schema import PathParam, get


class Invoice(BaseModel):
    invoice_id: str


@get("/invoices/{invoice_id}")
async def find_invoice(
    invoice_id: Annotated[str, PathParam()],
) -> Result[Invoice]:
    raise NotImplementedError


@get("/invoices/{invoice_id}", statuses={404: None})
async def maybe_invoice(
    invoice_id: Annotated[str, PathParam()],
) -> Result[Invoice | None]:
    raise NotImplementedError


async def check(client: HttpClient) -> None:
    found = await bind(find_invoice, client)("invoice-1")
    maybe = await bind(maybe_invoice, client)("invoice-2")

    assert_type(found, Result[Invoice])
    assert_type(found.value, Invoice)
    assert_type(maybe, Result[Invoice | None])
    assert_type(maybe.value, Invoice | None)
