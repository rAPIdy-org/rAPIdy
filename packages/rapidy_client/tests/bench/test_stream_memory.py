from __future__ import annotations

import subprocess
import sys
import tracemalloc
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
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
_TOTAL_BYTES = 2 * 1024**3
_PEAK_LIMIT = 32 * 1024**2
_CHUNK = b"\0" * _CHUNK_SIZE


async def _chunks(total_bytes: int) -> AsyncIterator[bytes]:
    for _ in range(total_bytes // _CHUNK_SIZE):
        yield _CHUNK


async def _consume(total_bytes: int = _TOTAL_BYTES) -> tuple[int, int]:
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
    tracemalloc.start()
    try:
        consumed = 0
        async with client.stream("GET", "/big") as response:
            async for chunk in response.aiter_bytes(_CHUNK_SIZE):
                consumed += len(chunk)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        await client.aclose()
    return consumed, peak


@pytest.mark.asyncio
async def test_tracemalloc_2gib_stream() -> None:
    consumed, peak = await _consume()

    assert consumed == _TOTAL_BYTES
    assert peak <= _PEAK_LIMIT


@pytest.mark.skipif(sys.platform != "linux", reason="linux-only RLIMIT_AS job")
def test_rlimit_as_2gib_stream() -> None:
    script = f"""
import asyncio
import resource

limit = 512 * 1024**2
_, hard = resource.getrlimit(resource.RLIMIT_AS)
resource.setrlimit(resource.RLIMIT_AS, (limit, min(limit, hard)))
from benchmarks._memory_child import consume

asyncio.run(consume({_TOTAL_BYTES}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        cwd=Path(__file__).parents[2],
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
