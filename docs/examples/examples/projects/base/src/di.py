from functools import wraps
from typing import Any, Callable, cast, ParamSpec, TypeVar

from dishka import AsyncContainer
from dishka.integrations.base import wrap_injection

T = TypeVar("T")
P = ParamSpec("P")


class _DIContextHolder:
    container: AsyncContainer


def init_di_holder(container: AsyncContainer) -> None:
    _DIContextHolder.container = container


def inject(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Callable[P, T]:  # noqa: ANN401
        async with _DIContextHolder.container() as request_dishka:
            wrapped = wrap_injection(
                func=func,
                remove_depends=True,
                container_getter=lambda _, __: request_dishka,
                is_async=True,
            )
            return await wrapped(*args, **kwargs)

    return cast(Callable[P, T], wrapper)
