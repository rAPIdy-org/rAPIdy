from __future__ import annotations

import asyncio
from typing import Annotated

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel
from rapidy_client import HttpClient, Response, UpstreamConfig, bind, post
from rapidy_client.schema import Body
from rapidy_client.testing import MockTransport


class Payload(BaseModel):
    identifier: int
    note: str | None
    tags: list[str]


@post("/payload")
async def send_payload(payload: Annotated[Payload, Body()]) -> Response:
    raise NotImplementedError


@settings(max_examples=30, deadline=None)
@given(
    identifier=st.integers(),
    note=st.one_of(st.none(), st.text()),
    tags=st.lists(st.text(), max_size=8),
)
def test_roundtrip_request_bytes_are_identical(
    identifier: int,
    note: str | None,
    tags: list[str],
) -> None:
    async def scenario() -> None:
        mock = MockTransport()
        mock.route("POST", "/payload").times(2).respond()
        client = HttpClient(
            UpstreamConfig(base_url="https://mock.test"),
            transport=mock,
        )
        endpoint = bind(send_payload, client)
        payload = Payload(identifier=identifier, note=note, tags=tags)
        try:
            await endpoint(payload)
            await endpoint(payload)
        finally:
            await client.aclose()

        assert mock.calls[0].request.content == mock.calls[1].request.content
        assert (
            mock.calls[0].request.headers.multi_items()
            == mock.calls[1].request.headers.multi_items()
        )

    asyncio.run(scenario())
