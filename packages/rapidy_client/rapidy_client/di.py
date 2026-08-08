from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from types import TracebackType
from typing import Annotated, Any, ParamSpec, Self, TypeVar, cast

from rapidy_core.di import (
    AsyncContainer,
    Component,
    FromComponent,
    Provider,
    Scope,
    make_async_container,
)

from rapidy_client._client import HttpClient
from rapidy_client._typed import bind
from rapidy_client.config import UpstreamConfig

P = ParamSpec("P")
R = TypeVar("R")
C = TypeVar("C")


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


def provide_controller(
    controller: type[C],
    *,
    component: Component,
) -> Provider:
    provider = Provider()

    def factory(client: HttpClient) -> C:
        return bind(controller, client)

    factory.__annotations__ = {
        "client": Annotated[HttpClient, FromComponent(component)],
        "return": controller,
    }
    provider.provide(factory, scope=Scope.APP, provides=controller)
    return provider


def provide_endpoint(
    endpoint: Callable[P, Awaitable[R]],
    *,
    provides: Any,
    component: Component,
) -> Provider:
    provider = Provider()

    def factory(client: HttpClient) -> Callable[P, Awaitable[R]]:
        return bind(endpoint, client)

    factory.__annotations__ = {
        "client": Annotated[HttpClient, FromComponent(component)],
        "return": provides,
    }
    provider.provide(factory, scope=Scope.APP, provides=provides)
    return provider


class RapidyClientProvider:
    upstream = staticmethod(provide_upstream)
    controller = staticmethod(provide_controller)
    endpoint = staticmethod(provide_endpoint)


class HttpApp:
    def __init__(
        self,
        upstreams: Mapping[Component, UpstreamConfig],
        controllers: Mapping[type[Any], Component] | None = None,
        di_providers: Sequence[Provider] = (),
    ) -> None:
        self._upstreams = dict(upstreams)
        self._controllers = dict(controllers or {})
        self._di_providers = tuple(di_providers)
        self._container: AsyncContainer | None = None

    @property
    def container(self) -> AsyncContainer:
        if self._container is None:
            raise RuntimeError("HttpApp is not entered")
        return self._container

    async def __aenter__(self) -> Self:
        if self._container is not None:
            raise RuntimeError("HttpApp cannot be entered twice")
        providers = [
            *(
                provide_upstream(component, config)
                for component, config in self._upstreams.items()
            ),
            *(
                provide_controller(controller, component=component)
                for controller, component in self._controllers.items()
            ),
            *self._di_providers,
        ]
        container = make_async_container(*providers)
        self._container = container
        try:
            for component in self._upstreams:
                await container.get(HttpClient, component=component)
            for controller in self._controllers:
                await container.get(controller)
        except BaseException as exc:
            self._container = None
            await container.close(exception=exc)
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del exc_type, tb
        container = self._container
        self._container = None
        if container is not None:
            await container.close(exception=exc)

    async def controller(self, controller: type[C]) -> C:
        if controller not in self._controllers:
            raise LookupError(
                f"controller {controller.__qualname__!r} is not registered"
            )
        return cast(C, await self.container.get(controller))


__all__ = (
    "HttpApp",
    "RapidyClientProvider",
    "provide_controller",
    "provide_endpoint",
    "provide_upstream",
)
