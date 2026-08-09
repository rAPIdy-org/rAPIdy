from __future__ import annotations

import asyncio
import gzip
import json
import pkgutil
import tempfile
from importlib import import_module, metadata
from pathlib import Path
from typing import Any

import rapidy
from rapidy import Rapidy
from rapidy.background import BackgroundTask
from rapidy.http import Response, get
from rapidy.middlewares import (
    CompressionMiddleware,
    GZipMiddleware,
    MissingBrotliDependencyError,
    RequestIDMiddleware,
)
from rapidy.responses import FileResponse
from rapidy.staticfiles import StaticFiles

OPTIONAL_IMPORT_PREFIXES = ('rapidy.testing',)


background_events: list[str] = []


@get("/")
async def hello() -> Response:
    return Response(
        {"message": "wheel-ok" * 100},
        background=BackgroundTask(background_events.append, "completed"),
    )


async def call(app: Rapidy, path: str, headers: list[tuple[bytes, bytes]]) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    received = False
    wait = asyncio.Event()

    async def receive() -> dict[str, Any]:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await wait.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "state": {},
    }
    await app(scope, receive, send)
    return sent


async def smoke() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        file_path = root / "wheel.txt"
        file_path.write_text("file-wheel-ok")

        @get("/file")
        async def file_handler() -> FileResponse:
            return FileResponse(file_path)

        app = Rapidy(
            http_route_handlers=[hello, file_handler, StaticFiles("/assets", directory=root)],
            middlewares=[RequestIDMiddleware(generator=lambda: "wheel-request"), GZipMiddleware(minimum_size=1)],
        )
        async with app.lifespan.ctx_manager():
            sent = await call(
                app,
                "/",
                [(b"host", b"testserver"), (b"accept-encoding", b"gzip")],
            )
            file_sent = await call(app, "/file", [(b"host", b"testserver")])
            static_sent = await call(app, "/assets/wheel.txt", [(b"host", b"testserver")])
        assert sent[0]["status"] == 200
        response_headers = {bytes(name).lower(): value for name, value in sent[0]["headers"]}
        assert response_headers[b"content-encoding"] == b"gzip"
        assert response_headers[b"x-request-id"] == b"wheel-request"
        assert json.loads(gzip.decompress(sent[1]["body"])) == {"message": "wheel-ok" * 100}
        assert background_events == ["completed"]
        assert b"".join(message.get("body", b"") for message in file_sent[1:]) == b"file-wheel-ok"
        assert b"".join(message.get("body", b"") for message in static_sent[1:]) == b"file-wheel-ok"


def main() -> int:
    assert metadata.version("rapidy") == "2.0.0"
    assert rapidy.__version__ == "2.0.0"
    requirements = metadata.requires("rapidy") or []
    assert not any(requirement.lower().startswith(("aiohttp", "dishka")) for requirement in requirements)
    assert all(
        not requirement.lower().startswith("uvicorn") or "extra ==" in requirement
        for requirement in requirements
    )
    try:
        metadata.version("uvicorn")
    except metadata.PackageNotFoundError:
        pass
    else:
        raise AssertionError("Uvicorn must stay optional in the base rAPIdy wheel")
    try:
        metadata.version("aiohttp")
    except metadata.PackageNotFoundError:
        pass
    else:
        raise AssertionError("aiohttp must not be installed with the rAPIdy 2.0 wheel")
    for module in pkgutil.walk_packages(rapidy.__path__, f"{rapidy.__name__}."):
        if any(
            module.name == prefix or module.name.startswith(f'{prefix}.')
            for prefix in OPTIONAL_IMPORT_PREFIXES
        ):
            continue
        import_module(module.name)
    try:
        CompressionMiddleware(algorithms=["br"])
    except MissingBrotliDependencyError:
        pass
    else:
        raise AssertionError("Brotli must stay optional in the base rAPIdy wheel")
    asyncio.run(smoke())
    print("rapidy wheel imports and ASGI quickstart: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
