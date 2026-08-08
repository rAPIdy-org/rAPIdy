from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st
from rapidy_client.sse import ServerSentEvent, SSEDecoder

_PAYLOAD = "\ufeffid: 7\r\nevent: update\ndata: привет\ndata: world\r\n\r\n".encode()


async def _chunks(parts: list[bytes]) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


async def _decode(parts: list[bytes]) -> list[ServerSentEvent]:
    decoder = SSEDecoder()
    return [event async for event in decoder.iter_bytes(_chunks(parts))]


@given(st.lists(st.integers(min_value=0, max_value=len(_PAYLOAD)), max_size=20))
def test_sse_decoder_is_invariant_to_chunk_splices(offsets: list[int]) -> None:
    points = [0, *sorted(set(offsets)), len(_PAYLOAD)]
    parts = [_PAYLOAD[start:end] for start, end in pairwise(points) if start != end]

    assert asyncio.run(_decode(parts)) == asyncio.run(_decode([_PAYLOAD]))
