from __future__ import annotations

import asyncio
import json
import pkgutil
from importlib import import_module, metadata
from typing import Any

import rapidy
from rapidy import Rapidy
from rapidy.http import get


@get("/")
async def hello() -> dict[str, str]:
    return {"message": "wheel-ok"}


async def smoke() -> None:
    app = Rapidy(http_route_handlers=[hello])
    sent: list[dict[str, Any]] = []
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "state": {},
    }
    async with app.lifespan.ctx_manager():
        await app(scope, receive, send)
    assert sent[0]["status"] == 200
    assert json.loads(sent[1]["body"]) == {"message": "wheel-ok"}


def main() -> int:
    assert metadata.version("rapidy") == "2.0.0"
    assert rapidy.__version__ == "2.0.0"
    requirements = metadata.requires("rapidy") or []
    assert not any(requirement.lower().startswith(("aiohttp", "dishka")) for requirement in requirements)
    try:
        metadata.version("aiohttp")
    except metadata.PackageNotFoundError:
        pass
    else:
        raise AssertionError("aiohttp must not be installed with the rAPIdy 2.0 wheel")
    for module in pkgutil.walk_packages(rapidy.__path__, f"{rapidy.__name__}."):
        import_module(module.name)
    asyncio.run(smoke())
    print("rapidy wheel imports and ASGI quickstart: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
