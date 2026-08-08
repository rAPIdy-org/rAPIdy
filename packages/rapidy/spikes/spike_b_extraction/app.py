from __future__ import annotations

import json
from typing import Any

from spikes._mini.asgi_app import Send, send_response
from spikes.spike_b_extraction.extraction_proto import (
    FileField,
    RequestEntityTooLarge,
    RequestProto,
)


class SpikeBApp:
    async def __call__(self, scope: dict[str, Any], receive: Any, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http" or scope.get("path") != "/multipart":
            await send_response(send, 404, b"not found")
            return
        request = RequestProto(scope, receive, client_max_size=1024**2)
        try:
            form = await request.post()
        except RequestEntityTooLarge:
            await send_response(send, 413, b"too large")
            return
        values: list[dict[str, Any]] = []
        for key, value in form.items():
            if isinstance(value, FileField):
                values.append(
                    {
                        "key": key,
                        "filename": value.filename,
                        "size": len(value.file.read()),
                    }
                )
            else:
                values.append({"key": key, "value": value})
        await send_response(
            send,
            200,
            json.dumps(values).encode(),
            headers=[(b"content-type", b"application/json")],
        )


app = SpikeBApp()

__all__ = ("SpikeBApp", "app")
