from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rapidy_client import HttpClient
from rapidy_client.testing import ChaosServer, FakeClock, MockTransport
from rapidy_client.testing.plugin import (
    chaos_server,
    fake_clock,
    http_client_factory,
    mock_transport,
)

if TYPE_CHECKING:
    from rapidy_client.testing.plugin import HttpClientFactory


def test_fixtures_importable() -> None:
    fixtures = (mock_transport, http_client_factory, fake_clock, chaos_server)

    assert all(callable(fixture) for fixture in fixtures)
    assert all(hasattr(fixture, "_fixture_function_marker") for fixture in fixtures)


def test_mock_transport_fixture_type(mock_transport: MockTransport) -> None:
    assert isinstance(mock_transport, MockTransport)


def test_fake_clock_fixture_type(fake_clock: FakeClock) -> None:
    assert isinstance(fake_clock, FakeClock)
    assert fake_clock.monotonic() == 0.0


@pytest.mark.asyncio
async def test_http_client_factory_builds_working_client(
    http_client_factory: HttpClientFactory,
    mock_transport: MockTransport,
) -> None:
    mock_transport.route("GET", "/ping").respond(status=200)

    client = http_client_factory()
    response = await client.get("/ping")

    assert isinstance(client, HttpClient)
    assert response.status == 200


@pytest.mark.asyncio
async def test_chaos_server_fixture_wraps_class(
    chaos_server: ChaosServer,
) -> None:
    assert isinstance(chaos_server, ChaosServer)
    assert chaos_server.url.startswith("http://127.0.0.1:")
    assert chaos_server.port > 0
