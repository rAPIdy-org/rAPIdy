from __future__ import annotations

from collections.abc import AsyncIterator

from rapidy_client import (
    Headers,
    HttpClient,
    Response,
    ResponseExtensions,
    UpstreamConfig,
)
from rapidy_client._models import Request
from rapidy_client.testing import MockTransport

_CHUNK_SIZE = 65536
_CHUNK = b"\0" * _CHUNK_SIZE


async def _chunks(total_bytes: int) -> AsyncIterator[bytes]:
    for _ in range(total_bytes // _CHUNK_SIZE):
        yield _CHUNK


async def consume(total_bytes: int) -> None:
    mock = MockTransport()

    async def handler(request: Request) -> Response:
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=0),
            stream=_chunks(total_bytes),
        )

    mock.route("GET", "/big").respond_with(handler)
    client = HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://memory.example.test",
                "log": {"level": "off"},
            }
        ),
        transport=mock,
    )
    consumed = 0
    try:
        async with client.stream("GET", "/big") as response:
            async for chunk in response.aiter_bytes(_CHUNK_SIZE):
                consumed += len(chunk)
    finally:
        await client.aclose()
    if consumed != total_bytes:
        raise RuntimeError(f"consumed {consumed} bytes instead of {total_bytes}")


__all__ = ("consume",)
