from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from rapidy import Rapidy


@pytest.mark.asyncio
async def test_lifespan_order() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def manager(app: Rapidy) -> AsyncIterator[None]:
        assert isinstance(app, Rapidy)
        events.append('ctx_enter')
        try:
            yield
        finally:
            events.append('ctx_exit')

    def startup(app: Rapidy) -> None:
        assert isinstance(app, Rapidy)
        events.append('on_startup')

    async def shutdown() -> None:
        events.append('on_shutdown')

    def cleanup() -> None:
        events.append('on_cleanup')

    app = Rapidy(
        lifespan=[manager],
        on_startup=[startup],
        on_shutdown=[shutdown],
        on_cleanup=[cleanup],
    )
    incoming = iter(({'type': 'lifespan.startup'}, {'type': 'lifespan.shutdown'}))
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        message = next(incoming)
        if message['type'] == 'lifespan.shutdown':
            events.append('work')
        return message

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app({'type': 'lifespan'}, receive, send)

    assert events == ['ctx_enter', 'on_startup', 'work', 'on_shutdown', 'on_cleanup', 'ctx_exit']
    assert sent == [
        {'type': 'lifespan.startup.complete'},
        {'type': 'lifespan.shutdown.complete'},
    ]


@pytest.mark.asyncio
async def test_startup_failure_sends_failed_message() -> None:
    def fail_startup() -> None:
        msg = 'startup exploded'
        raise RuntimeError(msg)

    app = Rapidy(on_startup=[fail_startup])
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {'type': 'lifespan.startup'}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    with pytest.raises(RuntimeError, match='startup exploded'):
        await app({'type': 'lifespan'}, receive, send)

    assert sent == [{'type': 'lifespan.startup.failed', 'message': 'startup exploded'}]


@pytest.mark.asyncio
async def test_shutdown_failure_sends_failed_message() -> None:
    async def fail_shutdown() -> None:
        msg = 'shutdown exploded'
        raise RuntimeError(msg)

    app = Rapidy(on_shutdown=[fail_shutdown])
    incoming = iter(({'type': 'lifespan.startup'}, {'type': 'lifespan.shutdown'}))
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return next(incoming)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    with pytest.raises(RuntimeError, match='shutdown exploded'):
        await app({'type': 'lifespan'}, receive, send)

    assert sent == [
        {'type': 'lifespan.startup.complete'},
        {'type': 'lifespan.shutdown.failed', 'message': 'shutdown exploded'},
    ]
