import inspect
from collections.abc import Callable
from inspect import Parameter
from typing import (
    Annotated,
    Any,
    Awaitable,
    Final,
    get_type_hints,
    ParamSpec,
    TypeAlias,
    TypeVar,
)

from dishka import (
    alias,
    AnyOf,
    AsyncContainer,
    BaseScope,
    Component,
    Container,
    decorate,
    DEFAULT_COMPONENT,
    DependencyKey,
    from_context,
    FromComponent,
    FromDishka as FromDI,
    make_async_container,
    make_container,
    new_scope,
    provide,
    provide_all,
    Provider,
    Scope,
    STRICT_VALIDATION,
    ValidationSettings,
    WithParents,
)
from dishka.integrations.base import wrap_injection

from rapidy.annotation_checkers import is_empty
from rapidy.enums import HeaderName
from rapidy.parameters.http import Header
from rapidy.typedefs import CallNext
from rapidy.version import AIOHTTP_VERSION_TUPLE
from rapidy.web_middlewares import middleware
from rapidy.web_request import Request
from rapidy.web_response import StreamResponse

__all__ = [
    'DEFAULT_COMPONENT',
    'STRICT_VALIDATION',
    'AnyOf',
    'AsyncContainer',
    'BaseScope',
    'Component',
    'Container',
    'FromDI',
    'DependencyKey',
    'Provider',
    'FromComponent',
    'Scope',
    'ValidationSettings',
    'WithParents',
    'alias',
    'decorate',
    'from_context',
    'make_async_container',
    'make_container',
    'new_scope',
    'provide',
    'provide_all',
    'Scope',
    'from_context',
    'make_async_container',
    'BaseScope',
]

if AIOHTTP_VERSION_TUPLE >= (3, 9, 0):
    from aiohttp.web import AppKey

    CONTAINER_KEY: Final[AppKey[AsyncContainer]] = AppKey(
        'container',
        AsyncContainer,
    )

else:
    CONTAINER_KEY: Final[str] = 'container'  # type: ignore[misc, no-redef]

UpgradeHeader: TypeAlias = Annotated[
    str | None,
    Header(alias=HeaderName.upgrade),
]
ConnectionHeader: TypeAlias = Annotated[
    str | None,
    Header(alias=HeaderName.connection),
]

P = ParamSpec('P')
T = TypeVar('T')


def inject_http(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    # WebSocket support will be added later
    return _inject_wrapper(func, 'request', Request)


def _inject_wrapper(
    func: Callable[P, T],
    param_name: str,
    param_annotation: type[Request],
) -> Callable[P, T]:
    hints = get_type_hints(
        func,
        # necessary because `rapidy` uses `if TYPE_CHECKING:`
        globalns={
            'Request': param_annotation,
            'StreamResponse': StreamResponse,
        },
    )

    additional_params = []
    actual_param_name = param_name
    request_exists = any(value is param_annotation for value in hints.values())

    if not request_exists:
        endpoint_signature = inspect.signature(func)
        endpoint_signature_params = endpoint_signature.parameters
        if not endpoint_signature_params:
            additional_params = [
                Parameter(name=actual_param_name, annotation=param_annotation, kind=Parameter.KEYWORD_ONLY),
            ]
        else:
            first_param = next(iter(endpoint_signature_params.values()))
            # I don't like this check `first_param.name != 'self'`
            # but it's impossible to verify that it's a method in any other way without creating an instance.
            if is_empty(first_param.annotation) and first_param.name != 'self':
                actual_param_name = first_param.name
            else:
                additional_params = [
                    Parameter(name=actual_param_name, annotation=param_annotation, kind=Parameter.KEYWORD_ONLY),
                ]

    def _get_depends(args: tuple[Any, ...], func_kwargs: dict[str, Any]) -> Any:
        try:
            current_request = func_kwargs[actual_param_name]
        except KeyError:
            for arg in args:
                if isinstance(arg, param_annotation):
                    return arg[CONTAINER_KEY]
            raise
        return current_request[CONTAINER_KEY]

    return wrap_injection(
        func=func,
        is_async=True,
        additional_params=additional_params,
        container_getter=_get_depends,
    )


class RapidyProvider(Provider):
    request = from_context(Request, scope=Scope.SESSION)
    # WebSocket support will be added later.


@middleware
async def di_middleware(
    request: Request,
    call_next: CallNext,
    *,
    upgrade_header: UpgradeHeader = None,
    connection_header: ConnectionHeader = None,
) -> StreamResponse:
    container = request.app[CONTAINER_KEY]

    scope = Scope.SESSION if upgrade_header == 'websocket' and connection_header == 'Upgrade' else Scope.REQUEST

    context = {Request: request}

    async with container(context=context, scope=scope) as request_container:
        request[CONTAINER_KEY] = request_container
        return await call_next(request)
