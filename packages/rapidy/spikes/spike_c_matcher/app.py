from __future__ import annotations

from typing import Any

from spikes._mini.asgi_app import Send, send_response
from spikes.spike_c_matcher.matcher_proto import MethodNotAllowed, NotFound, UrlMatcher


async def user_handler(user_id: str) -> bytes:
    return f"user:{user_id}".encode()


class SpikeCApp:
    def __init__(self) -> None:
        self.matcher = UrlMatcher()
        self.matcher.add_route("GET", "/users/{user_id}", user_handler, {"status": 200})
        self.matcher.add_route("GET", "/users/me", lambda: b"static", {"status": 200})

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            raise RuntimeError(scope["type"])
        method = scope["method"].upper()
        try:
            match = self.matcher.resolve(method, scope["path"])
        except NotFound:
            await send_response(send, 404, b"not found")
            return
        except MethodNotAllowed as error:
            allow = ", ".join(error.allowed_methods).encode()
            await send_response(
                send, 405, b"method not allowed", headers=[(b"allow", allow)]
            )
            return

        if scope["path"] == "/users/me":
            body = b"static"
        else:
            body = await match.terminal(**match.path_params)
        if method == "HEAD":
            await send(
                {
                    "type": "http.response.start",
                    "status": match.route_kwargs["status"],
                    "headers": [(b"content-length", str(len(body)).encode())],
                },
            )
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        await send_response(send, match.route_kwargs["status"], body)


app = SpikeCApp()

__all__ = ("SpikeCApp", "app", "user_handler")
