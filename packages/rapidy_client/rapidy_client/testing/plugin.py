from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

import pytest
import pytest_asyncio

from rapidy_client._client import HttpClient
from rapidy_client._clock import Clock
from rapidy_client._models import BaseTransport
from rapidy_client.config import UpstreamConfig
from rapidy_client.testing import FakeClock, MockTransport
from rapidy_client.testing.chaos import ChaosServer


class HttpClientFactory(Protocol):
    def __call__(
        self,
        base_url: str = "https://mock.test",
        *,
        transport: BaseTransport | None = None,
        clock: Clock | None = None,
        name: str = "default",
        **overrides: Any,
    ) -> HttpClient: ...


@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest_asyncio.fixture
async def http_client_factory(
    mock_transport: MockTransport,
    fake_clock: FakeClock,
) -> AsyncIterator[HttpClientFactory]:
    created: list[HttpClient] = []

    def _factory(
        base_url: str = "https://mock.test",
        *,
        transport: BaseTransport | None = None,
        clock: Clock | None = None,
        name: str = "default",
        **overrides: Any,
    ) -> HttpClient:
        config = UpstreamConfig.model_validate({"base_url": base_url, **overrides})
        client = HttpClient(
            config,
            name=name,
            transport=transport if transport is not None else mock_transport,
            _clock=clock if clock is not None else fake_clock,
        )
        created.append(client)
        return client

    yield _factory
    for client in created:
        await client.aclose()


@pytest_asyncio.fixture
async def chaos_server() -> AsyncIterator[ChaosServer]:
    async with ChaosServer() as server:
        yield server
