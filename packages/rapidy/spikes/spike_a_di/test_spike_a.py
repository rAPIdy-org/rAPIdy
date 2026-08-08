from __future__ import annotations

import inspect

import httpx
import pytest
from rapidy_core import di
from rapidy_core.di import Scope, make_async_container

from spikes._mini.request_proto import Request
from spikes._mini.serve import live_server
from spikes._mini.testing import CountingReceive, make_scope
from spikes.spike_a_di.app import (
    AppSingleton,
    MarkerDep,
    NeedsRequest,
    SessionMarkerDep,
    SpikeProvider,
)


@pytest.mark.asyncio
async def test_session_binding_resolves_in_request_scope() -> None:
    events: list[str] = []
    request = Request(make_scope(), CountingReceive([]))
    async with make_async_container(SpikeProvider(events)) as container:
        async with container(
            context={Request: request}, scope=Scope.REQUEST
        ) as request_container:
            assert await request_container.get(Request) is request
            assert (await request_container.get(NeedsRequest)).request is request
            assert isinstance(await request_container.get(MarkerDep), MarkerDep)
        assert events == ["finalizer"]


@pytest.mark.asyncio
async def test_session_scope_model_finalizes_once() -> None:
    events: list[str] = []
    async with make_async_container(SpikeProvider(events)) as container:
        async with container(scope=Scope.SESSION) as session_container:
            assert isinstance(
                await session_container.get(SessionMarkerDep), SessionMarkerDep
            )
        assert events == ["session_finalizer"]


@pytest.mark.asyncio
async def test_root_container_is_shared_by_subapp_model() -> None:
    events: list[str] = []
    first_request = Request(make_scope(path="/root"), CountingReceive([]))
    second_request = Request(make_scope(path="/sub"), CountingReceive([]))
    async with make_async_container(SpikeProvider(events)) as container:
        async with container(
            context={Request: first_request}, scope=Scope.REQUEST
        ) as first:
            singleton = await first.get(AppSingleton)
        async with container(
            context={Request: second_request}, scope=Scope.REQUEST
        ) as second:
            assert await second.get(AppSingleton) is singleton


def test_spike_imports_di_only_through_core_facade() -> None:
    import spikes.spike_a_di.app as spike_module

    source = inspect.getsource(spike_module)
    assert "from dishka" not in source
    assert "import dishka" not in source
    assert di.FromDI.__module__.startswith("dishka")


@pytest.mark.parametrize("runtime", ["granian", "uvicorn"])
def test_finalizer_after_response_once(runtime: str) -> None:
    with live_server(runtime, "spikes.spike_a_di.app:app") as base_url:
        with httpx.Client(base_url=base_url, timeout=10) as client:
            assert client.get("/reset").status_code == 204
            response = client.get("/probe")
            assert response.status_code == 200
            assert response.content == b"ok"
            events = client.get("/events").json()
    assert events == ["handler", "response_sent", "finalizer"]
    assert events.count("finalizer") == 1
