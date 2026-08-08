from __future__ import annotations

from collections.abc import AsyncIterator

from rapidy_core.di import Component, Provider, Scope

from rapidy_client._client import HttpClient
from rapidy_client.config import UpstreamConfig


def provide_upstream(component: Component, config: UpstreamConfig) -> Provider:
    provider = Provider(component=component)

    async def factory() -> AsyncIterator[HttpClient]:
        client = HttpClient(config, name=component)
        try:
            yield client
        finally:
            await client.aclose()

    provider.provide(factory, scope=Scope.APP, provides=HttpClient)
    return provider


__all__ = ("provide_upstream",)
