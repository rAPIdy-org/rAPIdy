from __future__ import annotations

import inspect
from typing import Annotated

import dishka
import pytest
from rapidy_core import di
from rapidy_core.di import (
    FromComponent,
    FromDI,
    Provider,
    Scope,
    make_async_container,
    make_container,
    provide,
)


class _SyncProvider(Provider):
    @provide(scope=Scope.APP)
    def number(self) -> int:
        return 42


class _AsyncProvider(Provider):
    @provide(scope=Scope.APP)
    async def number(self) -> int:
        return 43


class _LeftProvider(Provider):
    component = "left"

    @provide(scope=Scope.APP)
    def value(self) -> str:
        return "left"


class _RightProvider(Provider):
    component = "right"

    @provide(scope=Scope.APP)
    def value(self) -> str:
        return "right"


def test_public_surface_exact() -> None:
    assert set(di.__all__) == {
        "DEFAULT_COMPONENT",
        "STRICT_VALIDATION",
        "AnyOf",
        "AsyncContainer",
        "BaseScope",
        "Component",
        "Container",
        "DependencyKey",
        "FromComponent",
        "FromDI",
        "Provider",
        "Scope",
        "ValidationSettings",
        "WithParents",
        "alias",
        "decorate",
        "from_context",
        "make_async_container",
        "make_container",
        "new_scope",
        "provide",
        "provide_all",
        "wrap_injection",
    }


def test_from_di_is_from_dishka() -> None:
    assert FromDI is dishka.FromDishka


def test_sync_container_resolves_dependency() -> None:
    container = make_container(_SyncProvider())
    try:
        assert container.get(int) == 42
    finally:
        container.close()


@pytest.mark.asyncio
async def test_async_container_resolves_dependency() -> None:
    container = make_async_container(_AsyncProvider())
    try:
        assert await container.get(int) == 43
    finally:
        await container.close()


def test_components_disambiguate_same_type() -> None:
    container = make_container(_LeftProvider(), _RightProvider())

    def select(value: Annotated[str, FromComponent("right")]) -> str:
        return value

    wrapped = di.wrap_injection(
        func=select,
        container_getter=lambda _args, _kwargs: container,
        remove_depends=True,
    )
    try:
        assert container.get(str, component="left") == "left"
        assert wrapped() == "right"
    finally:
        container.close()


def test_wrap_injection_removes_dependency_from_signature() -> None:
    container = make_container(_SyncProvider())

    def endpoint(number: FromDI[int]) -> int:
        return number

    wrapped = di.wrap_injection(
        func=endpoint,
        container_getter=lambda _args, _kwargs: container,
        remove_depends=True,
    )
    try:
        assert inspect.signature(wrapped).parameters == {}
        assert wrapped() == 42
    finally:
        container.close()


def test_no_consumer_specific_names() -> None:
    names = (
        "container_getter",
        "additional_params",
        "middleware",
        "request_provider",
        "session_provider",
    )
    assert all(not hasattr(di, name) for name in names)
