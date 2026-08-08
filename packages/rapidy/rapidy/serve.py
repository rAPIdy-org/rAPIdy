from __future__ import annotations

from typing import Any

from rapidy.typedefs import ASGIApp

__all__ = ('run_app',)


def run_app(
    app: ASGIApp | str,
    host: str = '0.0.0.0',  # noqa: S104
    port: int = 8080,
    *,
    workers: int = 1,
    workers_kill_timeout: int | None = None,
    **server_kwargs: Any,
) -> None:
    """Run an ASGI application through Granian's programmatic API."""
    try:
        from granian.constants import Interfaces  # noqa: PLC0415
        from granian.server import Server  # noqa: PLC0415
    except ImportError as exc:
        msg = "Granian is required to run the server; install 'rapidy[granian]'"
        raise RuntimeError(msg) from exc

    target = app if isinstance(app, str) else f'{app.__class__.__module__}:{app.__class__.__qualname__}'
    server = Server(
        target=target,
        address=host,
        port=port,
        interface=Interfaces.ASGI,
        workers=workers,
        workers_kill_timeout=workers_kill_timeout,
        **server_kwargs,
    )
    if isinstance(app, str):
        server.serve()
    else:
        server.serve(target_loader=lambda _target: app)
