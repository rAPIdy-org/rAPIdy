from __future__ import annotations

import functools
import inspect
import re
import types
import typing
from collections.abc import Awaitable, Callable, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Generic,
    Literal,
    ParamSpec,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from pydantic import BaseModel, TypeAdapter
from rapidy_core import HTTPRequestParamType
from rapidy_core.signature import get_signature_raw_info
from rapidy_core.typedefs import Required, Undefined

from rapidy_client._client import HttpClient
from rapidy_client._declaration import declaration_body_is_declarative
from rapidy_client._models import QueryValue
from rapidy_client.errors import SchemaDefinitionError
from rapidy_client.schema._binding import bind as _bind_schema

if TYPE_CHECKING:
    from rapidy_core.fields.field_info import RapidyFieldInfo

    from rapidy_client.sse import SSEReconnect
    from rapidy_client.ws import Heartbeat

P = ParamSpec("P")
R = TypeVar("R")
C = TypeVar("C")

_PATH_PARAMETER = re.compile(r"\{([^{}/]+)\}")


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
    cast("Any", call).__signature__ = signature.replace(parameters=parameters)
    return call


class _ProtocolDeclaration(Generic[P, R]):
    def __init__(
        self,
        func: Callable[P, Awaitable[R]],
        *,
        kind: Literal["ws", "sse"],
        path: str,
        heartbeat: Any = None,
        max_message_size: int = 16_777_216,
        receive_queue_limit: int = 256,
        send_queue_limit: int = 256,
        send_timeout: float = 10.0,
        subprotocols: Sequence[str] = (),
        reconnect: Any = None,
        on_invalid: Literal["raise", "skip"] = "raise",
        last_event_id: str | None = None,
    ) -> None:
        self.func = func
        self.kind = kind
        self.path = path
        self.heartbeat = heartbeat
        self.max_message_size = max_message_size
        self.receive_queue_limit = receive_queue_limit
        self.send_queue_limit = send_queue_limit
        self.send_timeout = send_timeout
        self.subprotocols = tuple(subprotocols)
        self.reconnect = reconnect
        self.on_invalid = on_invalid
        self.last_event_id = last_event_id
        functools.update_wrapper(self, func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        del args, kwargs
        raise RuntimeError(
            f"{self.kind} declaration '{self.func.__qualname__}' is not bound to "
            f"a client; call bind({self.func.__name__}, client) first"
        )


def _check_declaration_body(func: Callable[..., Any]) -> None:
    qualname = func.__qualname__
    if not declaration_body_is_declarative(func):
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': body must contain only "
            "pass, ..., a docstring, or raise NotImplementedError"
        )


def _decorate_protocol(
    func: Callable[P, Awaitable[R]],
    **options: Any,
) -> Callable[P, Awaitable[R]]:
    if not inspect.iscoroutinefunction(func):
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{func.__qualname__}': declaration "
            "must be an async function"
        )
    _check_declaration_body(func)
    return cast(
        "Callable[P, Awaitable[R]]",
        _ProtocolDeclaration(func, **options),
    )


def ws(
    path: str,
    *,
    heartbeat: Heartbeat | None = None,
    max_message_size: int = 16_777_216,
    receive_queue_limit: int = 256,
    send_queue_limit: int = 256,
    send_timeout: float = 10.0,
    subprotocols: Sequence[str] = (),
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorate(
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        return _decorate_protocol(
            func,
            kind="ws",
            path=path,
            heartbeat=heartbeat,
            max_message_size=max_message_size,
            receive_queue_limit=receive_queue_limit,
            send_queue_limit=send_queue_limit,
            send_timeout=send_timeout,
            subprotocols=subprotocols,
        )

    return decorate


def sse(
    path: str,
    *,
    reconnect: SSEReconnect | None = None,
    on_invalid: Literal["raise", "skip"] = "raise",
    last_event_id: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorate(
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        return _decorate_protocol(
            func,
            kind="sse",
            path=path,
            reconnect=reconnect,
            on_invalid=on_invalid,
            last_event_id=last_event_id,
        )

    return decorate


def _is_model_annotation(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is typing.Annotated:
        args = get_args(annotation)
        return bool(args) and _is_model_annotation(args[0])
    if origin in (typing.Union, types.UnionType):
        args = get_args(annotation)
        return bool(args) and all(_is_model_annotation(item) for item in args)
    return (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and annotation is not BaseModel
    )


def _adapter(annotation: Any, qualname: str) -> TypeAdapter[Any]:
    if annotation is Any or not _is_model_annotation(annotation):
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': message type must be a "
            "concrete pydantic model or model union"
        )
    try:
        return TypeAdapter(annotation)
    except Exception as exc:
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': cannot compile message "
            f"type: {exc}"
        ) from exc


def _wire_name(field_info: RapidyFieldInfo) -> str:
    serialization_alias = field_info.serialization_alias
    if isinstance(serialization_alias, str):
        return serialization_alias
    alias = field_info.alias
    return alias if isinstance(alias, str) else field_info.name


def _marker_default(field_info: RapidyFieldInfo) -> object:
    default = field_info.default
    if default is Undefined or default is Required:
        return inspect.Parameter.empty
    return default


def _protocol_arguments(
    data_attrs: tuple[Any, ...],
    bound: inspect.BoundArguments,
) -> tuple[
    dict[str, object] | None,
    dict[str, QueryValue] | None,
    dict[str, str] | None,
]:
    from rapidy_client.schema._serialize import (
        expand_param_model,
        serialize_cookies,
        serialize_headers,
        serialize_query,
    )

    values = dict(bound.arguments)
    path_values: dict[str, object] = {}
    query_values: dict[str, QueryValue] = {}
    header_values: dict[str, object] = {}
    cookie_values: dict[str, object] = {}
    for data_attr in data_attrs:
        field_info = cast("RapidyFieldInfo", data_attr.field_info)
        name = field_info.name
        value = values.get(name, inspect.Parameter.empty)
        if value is inspect.Parameter.empty:
            value = _marker_default(field_info)
        if value is inspect.Parameter.empty:
            raise TypeError(f"missing required argument: '{name}'")
        wire_name = _wire_name(field_info)
        param_type = cast(
            "HTTPRequestParamType",
            getattr(field_info, "param_type", None),
        )
        extract_single = bool(getattr(field_info, "extract_single", False))
        if param_type is HTTPRequestParamType.path:
            if extract_single:
                path_values[name] = value
            elif isinstance(value, BaseModel):
                path_values.update(
                    expand_param_model(value, by_alias=True, exclude_none=True)
                )
            else:
                raise SchemaDefinitionError(
                    f"PathParams argument '{name}' must be a pydantic model"
                )
        elif param_type is HTTPRequestParamType.query:
            if extract_single:
                query_values[wire_name] = cast("QueryValue", value)
            elif isinstance(value, BaseModel):
                query_values.update(
                    cast(
                        "dict[str, QueryValue]",
                        expand_param_model(value, by_alias=True, exclude_none=True),
                    )
                )
            else:
                raise SchemaDefinitionError(
                    f"QueryParams argument '{name}' must be a pydantic model"
                )
        elif param_type is HTTPRequestParamType.header:
            if extract_single:
                header_values[wire_name] = value
            elif isinstance(value, BaseModel):
                header_values.update(
                    expand_param_model(value, by_alias=True, exclude_none=True)
                )
            else:
                raise SchemaDefinitionError(
                    f"Headers argument '{name}' must be a pydantic model"
                )
        elif param_type is HTTPRequestParamType.cookie:
            if extract_single:
                cookie_values[wire_name] = value
            elif isinstance(value, BaseModel):
                cookie_values.update(
                    expand_param_model(value, by_alias=True, exclude_none=True)
                )
            else:
                raise SchemaDefinitionError(
                    f"Cookies argument '{name}' must be a pydantic model"
                )

    query_pairs = serialize_query(query_values, list_style=None)
    query: dict[str, QueryValue] = {}
    for name, value in query_pairs:
        previous = query.get(name)
        if previous is None:
            query[name] = value
        elif isinstance(previous, list):
            previous.append(value)
        else:
            query[name] = [cast("str", previous), value]
    headers = dict(serialize_headers(header_values))
    cookie = serialize_cookies(cookie_values)
    if cookie:
        headers["Cookie"] = cookie
    return path_values or None, query or None, headers or None


def _bind_protocol(
    declaration: _ProtocolDeclaration[P, R],
    client: HttpClient,
) -> Callable[P, Awaitable[R]]:
    from rapidy_client.sse import SSEConnect, SSEStream
    from rapidy_client.ws import WSConnect, WSSocket

    qualname = declaration.func.__qualname__
    signature = inspect.signature(declaration.func)
    try:
        raw = get_signature_raw_info(declaration.func)
    except Exception as exc:
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': cannot resolve "
            f"annotations: {exc}"
        ) from exc
    return_annotation = raw.return_annotation
    origin = get_origin(return_annotation)
    type_args = get_args(return_annotation)
    expected = (WSSocket, WSConnect) if declaration.kind == "ws" else (SSEStream,)
    if origin not in expected:
        names = " or ".join(item.__name__ for item in expected)
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': @{declaration.kind} "
            f"must return {names} with concrete type arguments"
        )
    expected_count = 2 if origin is WSConnect else 1
    if len(type_args) != expected_count:
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': return handle requires "
            f"{expected_count} type argument(s)"
        )
    adapters = tuple(_adapter(item, qualname) for item in type_args)

    data_attrs = tuple(raw.data_attrs)
    marked_names = {item.field_info.name for item in data_attrs}
    if declaration.kind == "sse" and "last_event_id" in marked_names:
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': last_event_id is a "
            "reserved unmarked control argument"
        )
    for item in raw.attrs:
        name = item.attribute_name
        if name in marked_names:
            continue
        if declaration.kind == "sse" and name == "last_event_id":
            parameter = signature.parameters[name]
            if parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
                raise SchemaDefinitionError(
                    f"invalid protocol declaration '{qualname}': last_event_id "
                    "must be keyword-only"
                )
            if parameter.default is not None:
                raise SchemaDefinitionError(
                    f"invalid protocol declaration '{qualname}': last_event_id "
                    "must default to None"
                )
            continue
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': parameter '{name}' has "
            "no schema marker"
        )
    path_names = frozenset(_PATH_PARAMETER.findall(declaration.path))
    marked_paths: set[str] = set()
    for item in data_attrs:
        field_info = item.field_info
        if getattr(field_info, "param_type", None) is not HTTPRequestParamType.path:
            continue
        if bool(getattr(field_info, "extract_single", False)):
            marked_paths.add(field_info.name)
            continue
        model_fields = getattr(
            getattr(field_info, "annotation", None),
            "model_fields",
            {},
        )
        marked_paths.update(
            field.alias if isinstance(field.alias, str) else name
            for name, field in model_fields.items()
        )
    if path_names != marked_paths:
        raise SchemaDefinitionError(
            f"invalid protocol declaration '{qualname}': path parameters do not "
            "match PathParam markers"
        )
    for item in data_attrs:
        if getattr(item.field_info, "param_type", None) is HTTPRequestParamType.body:
            raise SchemaDefinitionError(
                f"invalid protocol declaration '{qualname}': protocol "
                "declarations cannot have body parameters"
            )

    @functools.wraps(declaration.func)
    async def call(*args: P.args, **kwargs: P.kwargs) -> R:
        bound = signature.bind(*args, **kwargs)
        last_id = declaration.last_event_id
        if declaration.kind == "sse" and "last_event_id" in bound.arguments:
            last_id = cast("str | None", bound.arguments.pop("last_event_id"))
        path_params, query, headers = _protocol_arguments(
            data_attrs,
            bound,
        )
        if declaration.kind == "ws":
            if origin is WSSocket:
                ws_connection = WSConnect[Any, Any](
                    client,
                    declaration.path,
                    heartbeat=declaration.heartbeat,
                    max_message_size=declaration.max_message_size,
                    receive_queue_limit=declaration.receive_queue_limit,
                    send_queue_limit=declaration.send_queue_limit,
                    send_timeout=declaration.send_timeout,
                    subprotocols=declaration.subprotocols,
                    headers=headers,
                    _send_adapter=adapters[0],
                    _recv_adapter=adapters[0],
                    _path_params=path_params,
                    _query=query,
                )
                return cast("R", WSSocket(ws_connection))
            ws_connection = WSConnect[Any, Any](
                client,
                declaration.path,
                heartbeat=declaration.heartbeat,
                max_message_size=declaration.max_message_size,
                receive_queue_limit=declaration.receive_queue_limit,
                send_queue_limit=declaration.send_queue_limit,
                send_timeout=declaration.send_timeout,
                subprotocols=declaration.subprotocols,
                headers=headers,
                _send_adapter=adapters[0],
                _recv_adapter=adapters[1],
                _path_params=path_params,
                _query=query,
            )
            return cast("R", ws_connection)
        sse_connection = SSEConnect[Any](
            client,
            declaration.path,
            last_event_id=last_id,
            reconnect=declaration.reconnect,
            headers=headers,
            _adapter=adapters[0],
            _on_invalid=declaration.on_invalid,
            _path_params=path_params,
            _query=query,
        )
        return cast("R", SSEStream(sse_connection))

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
    if isinstance(target, _ProtocolDeclaration):
        return _bind_protocol(target, client)
    return _bind_schema(target, cast("Any", client))


__all__ = ("Operation", "bind", "operation", "sse", "ws")
