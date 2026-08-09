from __future__ import annotations

from typing import Any

from rapidy_core.exceptions import RapidyException

from rapidy.typedefs import ASGIApp

__all__ = ('MissingUvicornDependencyError', 'run_app')


class MissingUvicornDependencyError(RapidyException):
    """Raised when the Uvicorn-oriented launcher is used without its server extra."""

    message = "Uvicorn is required for run_app and the rapidy CLI; install 'rapidy[uvicorn]'."


def run_app(
    app: ASGIApp | str,
    host: str = '0.0.0.0',  # noqa: S104
    port: int = 8080,
    *,
    workers: int = 1,
    timeout_graceful_shutdown: int | None = None,
    **server_kwargs: Any,
) -> None:
    """Run an ASGI application through Uvicorn's programmatic API."""
    try:
        import uvicorn  # noqa: PLC0415
    except ImportError as exc:
        raise MissingUvicornDependencyError from exc

    if not isinstance(app, str) and (workers != 1 or bool(server_kwargs.get('reload'))):
        msg = "Uvicorn reload and multiple workers require an application import string such as 'main:app'"
        raise ValueError(msg)

    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        timeout_graceful_shutdown=timeout_graceful_shutdown,
        **server_kwargs,
    )
