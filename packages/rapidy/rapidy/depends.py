from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from inspect import Parameter
from typing import Any, cast, get_type_hints

from rapidy_core import is_empty
from rapidy_core.di import (
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
    FromDI,
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
    wrap_injection,
)

from rapidy.request import Request
from rapidy.response import Response
from rapidy.websockets import WebSocket

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
]


def inject_http[**P, T](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Inject Dishka dependencies using the current HTTP request container."""
    return _inject_wrapper(func, 'request', Request)


def _inject_wrapper[**P, T](
    func: Callable[P, T],
    param_name: str,
    param_annotation: type[Request],
) -> Callable[P, T]:
    annotation_source = inspect.unwrap(func)
    global_namespace = dict(getattr(annotation_source, '__globals__', {}))
    global_namespace.update({'Request': Request, 'Response': Response})
    hints = get_type_hints(annotation_source, globalns=global_namespace, include_extras=True)

    additional_params: list[Parameter] = []
    actual_param_name = param_name
    endpoint_signature = inspect.signature(func)
    endpoint_signature_params = endpoint_signature.parameters

    request_param_name = next(
        (
            name
            for name in endpoint_signature_params
            if hints.get(name, endpoint_signature_params[name].annotation) is param_annotation
        ),
        None,
    )
    if request_param_name is not None:
        actual_param_name = request_param_name
    elif not endpoint_signature_params:
        additional_params = [
            Parameter(name=actual_param_name, annotation=param_annotation, kind=Parameter.KEYWORD_ONLY),
        ]
    else:
        first_param = next(iter(endpoint_signature_params.values()))
        if is_empty(first_param.annotation) and first_param.name != 'self':
            actual_param_name = first_param.name
        else:
            additional_params = [
                Parameter(name=actual_param_name, annotation=param_annotation, kind=Parameter.KEYWORD_ONLY),
            ]

    def container_getter(args: tuple[Any, ...], func_kwargs: dict[str, Any]) -> AsyncContainer:
        try:
            current_request = func_kwargs[actual_param_name]
        except KeyError:
            for arg in args:
                if isinstance(arg, param_annotation):
                    return cast('AsyncContainer', arg.state.di_container)
            raise
        return cast('AsyncContainer', current_request.state.di_container)

    return wrap_injection(
        func=func,
        is_async=True,
        additional_params=additional_params,
        remove_depends=True,
        container_getter=container_getter,
    )


class RapidyProvider(Provider):
    """Expose server context objects to user providers."""

    request = from_context(Request, scope=Scope.SESSION)
    web_socket = from_context(WebSocket, scope=Scope.SESSION)
