import asyncio
from collections.abc import AsyncIterator

from rapidy import Rapidy
from rapidy.http import get, SSEResponse, StreamResponse


@get('/sse')
async def sse_handler() -> SSEResponse:
    async def events() -> AsyncIterator[dict[str, int]]:
        for index in range(50):
            yield {'n': index}
            await asyncio.sleep(0.2)

    return SSEResponse(events())


@get('/stream')
async def stream_handler() -> StreamResponse:
    async def chunks() -> AsyncIterator[bytes]:
        yield b'chunk-1'
        await asyncio.sleep(0.1)
        yield b'chunk-2'

    return StreamResponse(body=chunks())


@get('/broken-stream')
async def broken_stream_handler() -> StreamResponse:
    async def chunks() -> AsyncIterator[bytes]:
        yield b'partial'
        msg = 'broken stream'
        raise RuntimeError(msg)

    return StreamResponse(body=chunks())


app = Rapidy(http_route_handlers=[sse_handler, stream_handler, broken_stream_handler])
