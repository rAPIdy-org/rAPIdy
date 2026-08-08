from __future__ import annotations

from rapidy.typedefs import Send

__all__ = ('close_unsupported_websocket',)


async def close_unsupported_websocket(send: Send) -> None:
    """Close WebSockets until the full contract is implemented in milestone 11."""
    await send({'type': 'websocket.close', 'code': 1011, 'reason': 'WebSocket support is not available yet'})
