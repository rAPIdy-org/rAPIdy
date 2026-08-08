from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio

from rapidy import Rapidy
from tests.ported.client import AppClient, AppClientFactory


@pytest_asyncio.fixture
async def app_client() -> AsyncIterator[AppClientFactory]:
    clients: list[AppClient] = []

    async def factory(app: Rapidy) -> AppClient:
        client = await AppClient.create(app)
        clients.append(client)
        return client

    yield factory

    for client in reversed(clients):
        await client.close()
