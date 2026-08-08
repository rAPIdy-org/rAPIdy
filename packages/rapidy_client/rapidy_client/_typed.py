from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import (
    Any,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
    get_type_hints,
    overload,
)

from rapidy_client._client import HttpClient
from rapidy_client.errors import SchemaDefinitionError
from rapidy_client.schema._binding import bind as _bind_schema

P = ParamSpec("P")
R = TypeVar("R")
C = TypeVar("C")


class Operation(Generic[P, R]):
    """A typed client-side operation with an injected leading client."""

    def __init__(
        self,
        func: Callable[Concatenate[HttpClient, P], Awaitable[R]],
    ) -> None:
        self.func = func
        functools.update_wrapper(self, func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        del args, kwargs
        raise RuntimeError(
            f"operation '{self.func.__qualname__}' is not bound to a client; "
            f"call bind({self.func.__name__}, client) first"
        )


def operation(
    func: Callable[Concatenate[HttpClient, P], Awaitable[R]],
) -> Operation[P, R]:
    qualname = func.__qualname__
    if not inspect.iscoroutinefunction(func):
        raise SchemaDefinitionError(
            f"invalid operation '{qualname}': operation must be an async function"
        )
    parameters = tuple(inspect.signature(func).parameters.values())
    if not parameters or parameters[0].name in {"self", "cls"}:
        raise SchemaDefinitionError(
            f"invalid operation '{qualname}': only a free function with a leading "
            "HttpClient parameter is supported"
        )
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception as exc:
        raise SchemaDefinitionError(
            f"invalid operation '{qualname}': cannot resolve annotations: {exc}"
        ) from exc
    first = parameters[0]
    if hints.get(first.name, first.annotation) is not HttpClient:
        raise SchemaDefinitionError(
            f"invalid operation '{qualname}': first parameter must be HttpClient"
        )
    return Operation(func)


def _bind_operation(
    target: Operation[P, R], client: HttpClient
) -> Callable[P, Awaitable[R]]:
    @functools.wraps(target.func)
    async def call(*args: P.args, **kwargs: P.kwargs) -> R:
        return await target.func(client, *args, **kwargs)

    signature = inspect.signature(target.func)
    parameters = tuple(signature.parameters.values())[1:]
    cast(Any, call).__signature__ = signature.replace(parameters=parameters)
    return call


@overload
def bind(target: Operation[P, R], client: HttpClient) -> Callable[P, Awaitable[R]]: ...


@overload
def bind(
    target: Callable[P, Awaitable[R]], client: HttpClient
) -> Callable[P, Awaitable[R]]: ...


@overload
def bind(target: type[C], client: HttpClient) -> C: ...


def bind(target: Any, client: HttpClient) -> Any:
    if isinstance(target, Operation):
        return _bind_operation(target, client)
    return _bind_schema(target, cast(Any, client))


__all__ = ("Operation", "bind", "operation")
