from __future__ import annotations

import ast
import functools
import inspect
import re
import textwrap
import types
import typing
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar, cast

from rapidy_core import UNSET, HTTPRequestParamType, Unset
from rapidy_core.fields.field_info import RapidyFieldInfo
from rapidy_core.signature import get_signature_raw_info
from rapidy_core.typedefs import Required, Undefined

from rapidy_client._models import Middleware, Response, Result, Timeout
from rapidy_client.errors import SchemaDefinitionError

if TYPE_CHECKING:
    from pydantic import BaseModel

    from rapidy_client.config import RetryConfig
    from rapidy_client.schema import CallOptions, QuerySerialization

P = ParamSpec("P")
R = TypeVar("R")
C = TypeVar("C", bound=type[Any])

_PATH_PARAM_RE = re.compile(r"\{([^{}/]+)\}")


class Stream:
    """Return marker for a lazy response stream."""

    __slots__ = ()


class _ClientLike(Protocol):
    async def request(self, method: str, path: str, **kwargs: Any) -> Response: ...

    def stream(
        self, method: str, path: str, **kwargs: Any
    ) -> AbstractAsyncContextManager[Response]: ...


type ErrorModel = type[BaseModel] | Mapping[int, type[BaseModel]] | None | Unset


@dataclass(frozen=True, slots=True)
class _EndpointDeclaration:
    http_method: str
    path_template: str
    func: Callable[..., Any]
    qualname: str
    has_self: bool
    path_param_names: frozenset[str]
    signature_param_names: tuple[str, ...]
    timeout: Timeout | float | None | Unset = UNSET
    retry: RetryConfig | None | Unset = UNSET
    deadline: float | Unset = UNSET
    follow_redirects: bool | Unset = UNSET
    idempotent: bool | Unset = UNSET
    statuses: Mapping[int, Any] | Unset = UNSET
    error_model: ErrorModel = UNSET
    query_serialization: QuerySerialization | Unset = UNSET
    name: str | Unset = UNSET
    middlewares: tuple[Middleware, ...] = ()
    serialization_options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _ControllerDeclaration:
    prefix: str
    cls_qualname: str
    timeout: Timeout | float | None | Unset = UNSET
    retry: RetryConfig | None | Unset = UNSET
    deadline: float | Unset = UNSET
    follow_redirects: bool | Unset = UNSET
    idempotent: bool | Unset = UNSET
    statuses: Mapping[int, Any] | Unset = UNSET
    error_model: ErrorModel = UNSET
    query_serialization: QuerySerialization | Unset = UNSET
    middlewares: tuple[Middleware, ...] = ()


@dataclass(frozen=True, slots=True)
class _EffectiveDeclaration:
    http_method: str
    full_path: str
    timeout: Timeout | float | None | Unset
    retry: RetryConfig | None | Unset
    deadline: float | Unset
    follow_redirects: bool | Unset
    idempotent: bool | Unset
    statuses: Mapping[int, Any] | Unset
    error_model: ErrorModel
    query_serialization: QuerySerialization | Unset
    name: str | Unset
    middlewares: tuple[Middleware, ...]
    serialization_options: Mapping[str, Any]
    declaration: _EndpointDeclaration


@dataclass(frozen=True, slots=True)
class _ResolvedSignature:
    data_attrs: tuple[Any, ...]
    signature: inspect.Signature
    return_annotation: Any
    returns_stream: bool
    returns_response: bool
    returns_none: bool


class Endpoint:
    """Immutable, unbound HTTP endpoint declaration."""

    def __init__(self, effective: _EffectiveDeclaration) -> None:
        self._effective = effective
        functools.update_wrapper(self, effective.declaration.func)

    @property
    def declaration(self) -> _EndpointDeclaration:
        return self._effective.declaration

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise RuntimeError(
            f"endpoint '{self._effective.declaration.qualname}' is not bound to a "
            f"client; call bind({self._effective.declaration.func.__name__}, client) "
            "first"
        )


class _BoundEndpoint:
    def __init__(
        self,
        client: _ClientLike,
        effective: _EffectiveDeclaration,
        resolved: _ResolvedSignature,
    ) -> None:
        self._client = client
        self._effective = effective
        self._resolved = resolved
        functools.update_wrapper(self, effective.declaration.func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        values = _call_values(self._effective, self._resolved, args, kwargs)
        return _dispatch(self._client, self._effective, self._resolved, values)


class _ControllerMethodDescriptor:
    def __init__(self, name: str) -> None:
        self._name = name

    def __get__(self, obj: object | None, owner: type[Any]) -> Any:
        effective = owner.__rapidy_endpoints__[self._name]
        if obj is None:
            return effective

        instance = cast(Any, obj)
        resolved = instance._rapidy_bound[self._name]
        client = instance._rapidy_client

        @functools.wraps(effective.declaration.func)
        def call(*args: Any, **kwargs: Any) -> Any:
            values = _call_values(effective, resolved, args, kwargs)
            return _dispatch(client, effective, resolved, values)

        parameters = tuple(resolved.signature.parameters.values())[1:]
        call.__signature__ = resolved.signature.replace(parameters=parameters)  # type: ignore[attr-defined]
        return call


def _path_param_names(template: str) -> frozenset[str]:
    return frozenset(_PATH_PARAM_RE.findall(template))


def _schema_error(qualname: str, message: str) -> SchemaDefinitionError:
    return SchemaDefinitionError(f"invalid endpoint '{qualname}': {message}")


def _check_async(func: Callable[..., Any], qualname: str) -> None:
    if not inspect.iscoroutinefunction(func):
        raise _schema_error(qualname, "declaration must be an async function")


def _check_empty_body(func: Callable[..., Any], qualname: str) -> None:
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    except (OSError, SyntaxError, TypeError) as exc:
        raise _schema_error(
            qualname, f"cannot inspect declaration body: {exc}"
        ) from exc

    node = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.AsyncFunctionDef) and item.name == func.__name__
        ),
        None,
    )
    if node is None:
        raise _schema_error(qualname, "cannot locate declaration body")

    body = list(node.body)
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body.pop(0)
    if not body:
        return
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return
    if len(body) == 1 and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and value.value is Ellipsis:
            return
    if len(body) == 1 and isinstance(body[0], ast.Raise):
        raised = body[0].exc
        if (
            isinstance(raised, ast.Call)
            and isinstance(raised.func, ast.Name)
            and raised.func.id == "NotImplementedError"
        ) or (isinstance(raised, ast.Name) and raised.id == "NotImplementedError"):
            return
    raise _schema_error(
        qualname,
        "body must contain only pass, ..., a docstring, or raise NotImplementedError",
    )


def _stage1_signature_scan(
    func: Callable[..., Any],
) -> tuple[bool, tuple[str, ...], dict[str, RapidyFieldInfo | None], frozenset[str]]:
    params = list(inspect.signature(func).parameters.items())
    has_self = bool(params) and params[0][0] == "self"
    marker_by_param: dict[str, RapidyFieldInfo | None] = {}
    deferred: set[str] = set()
    names: list[str] = []
    for pname, parameter in params:
        if (pname == "self" and has_self) or pname == "_options":
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        names.append(pname)
        marker: RapidyFieldInfo | None = None
        if isinstance(parameter.default, RapidyFieldInfo):
            marker = parameter.default
        elif not isinstance(parameter.annotation, str):
            metadata = getattr(parameter.annotation, "__metadata__", ())
            if metadata and isinstance(metadata[-1], RapidyFieldInfo):
                marker = metadata[-1]
        else:
            deferred.add(pname)
        marker_by_param[pname] = marker
    return has_self, tuple(names), marker_by_param, frozenset(deferred)


def _check_marking_and_paths(
    marker_by_param: Mapping[str, RapidyFieldInfo | None],
    path_names: frozenset[str],
    qualname: str,
    *,
    deferred: frozenset[str] = frozenset(),
) -> None:
    for pname, marker in marker_by_param.items():
        if marker is None and pname not in deferred:
            raise _schema_error(qualname, f"parameter '{pname}' has no schema marker")

    marked_paths = {
        pname
        for pname, marker in marker_by_param.items()
        if marker is not None
        and getattr(marker, "param_type", None) is HTTPRequestParamType.path
    }
    extra = marked_paths - path_names
    if extra:
        raise _schema_error(
            qualname,
            f"PathParam argument(s) {sorted(extra)} are absent from the path template",
        )
    if not deferred:
        missing = path_names - marked_paths
        if missing:
            raise _schema_error(
                qualname,
                f"path parameter(s) {sorted(missing)} have no PathParam argument",
            )


def _check_body_count(
    markers: Mapping[str, RapidyFieldInfo | None], qualname: str
) -> None:
    bodies = [
        name
        for name, marker in markers.items()
        if marker is not None
        and getattr(marker, "param_type", None) is HTTPRequestParamType.body
    ]
    if len(bodies) > 1:
        raise _schema_error(qualname, f"multiple body parameters: {bodies}")


def _check_statuses_error_model_conflict(
    statuses: Mapping[int, Any] | Unset,
    error_model: object,
    qualname: str,
) -> None:
    if statuses is UNSET:
        return
    invalid = [
        code for code in statuses if not isinstance(code, int) or not 100 <= code <= 599
    ]
    if invalid:
        raise _schema_error(qualname, f"invalid statuses keys: {invalid}")
    if isinstance(error_model, Mapping):
        overlap = set(statuses) & set(error_model)
        if overlap:
            raise _schema_error(
                qualname,
                f"status code(s) {sorted(overlap)} occur in statuses and error_model",
            )


def _annotation_members(annotation: Any) -> tuple[Any, ...]:
    if typing.get_origin(annotation) is Result:
        args = typing.get_args(annotation)
        if len(args) != 1:
            return ()
        annotation = args[0]
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        return tuple(
            member
            for arg in typing.get_args(annotation)
            for member in _annotation_members(arg)
        )
    return (annotation,)


def _check_statuses_coverage(
    statuses: Mapping[int, Any] | Unset,
    return_annotation: Any,
    qualname: str,
) -> None:
    if statuses is UNSET or not statuses:
        return
    members = _annotation_members(return_annotation)
    if Any in members or Response in members or Stream in members:
        return
    uncovered: dict[int, Any] = {}
    for code, value_type in statuses.items():
        expected = type(None) if value_type is None else value_type
        if expected not in members:
            uncovered[code] = value_type
    if uncovered:
        raise _schema_error(
            qualname,
            f"return annotation does not cover statuses values: {uncovered}",
        )


def _inherit(method_value: Any, controller_value: Any) -> Any:
    if method_value is not UNSET:
        return method_value
    return controller_value


def _join_path(prefix: str, relative: str) -> str:
    left = prefix.rstrip("/")
    right = relative if relative.startswith("/") else f"/{relative}"
    return f"{left}{right}" or "/"


def _effective_functional(declaration: _EndpointDeclaration) -> _EffectiveDeclaration:
    return _EffectiveDeclaration(
        http_method=declaration.http_method,
        full_path=declaration.path_template,
        timeout=declaration.timeout,
        retry=declaration.retry,
        deadline=declaration.deadline,
        follow_redirects=declaration.follow_redirects,
        idempotent=declaration.idempotent,
        statuses=declaration.statuses,
        error_model=declaration.error_model,
        query_serialization=declaration.query_serialization,
        name=declaration.name,
        middlewares=declaration.middlewares,
        serialization_options=declaration.serialization_options,
        declaration=declaration,
    )


def _effective_from_controller(
    controller_declaration: _ControllerDeclaration,
    method: _EndpointDeclaration,
) -> _EffectiveDeclaration:
    return _EffectiveDeclaration(
        http_method=method.http_method,
        full_path=_join_path(controller_declaration.prefix, method.path_template),
        timeout=_inherit(method.timeout, controller_declaration.timeout),
        retry=_inherit(method.retry, controller_declaration.retry),
        deadline=_inherit(method.deadline, controller_declaration.deadline),
        follow_redirects=_inherit(
            method.follow_redirects, controller_declaration.follow_redirects
        ),
        idempotent=_inherit(method.idempotent, controller_declaration.idempotent),
        statuses=_inherit(method.statuses, controller_declaration.statuses),
        error_model=_inherit(method.error_model, controller_declaration.error_model),
        query_serialization=_inherit(
            method.query_serialization, controller_declaration.query_serialization
        ),
        name=method.name,
        middlewares=controller_declaration.middlewares + method.middlewares,
        serialization_options=method.serialization_options,
        declaration=method,
    )


def _resolve_signature(effective: _EffectiveDeclaration) -> _ResolvedSignature:
    declaration = effective.declaration
    try:
        raw = get_signature_raw_info(declaration.func)
    except Exception as exc:
        raise _schema_error(
            declaration.qualname, f"cannot resolve schema annotations: {exc}"
        ) from exc

    marker_by_param: dict[str, RapidyFieldInfo | None] = {
        attr.field_info.name: attr.field_info for attr in raw.data_attrs
    }
    for attr in raw.attrs:
        if attr.attribute_name not in ("self", "_options"):
            marker_by_param.setdefault(attr.attribute_name, None)
    _check_marking_and_paths(
        marker_by_param,
        declaration.path_param_names,
        declaration.qualname,
    )
    _check_body_count(marker_by_param, declaration.qualname)
    _check_statuses_coverage(
        effective.statuses, raw.return_annotation, declaration.qualname
    )
    return_annotation = raw.return_annotation
    return _ResolvedSignature(
        data_attrs=tuple(raw.data_attrs),
        signature=inspect.signature(declaration.func),
        return_annotation=return_annotation,
        returns_stream=return_annotation is Stream,
        returns_response=return_annotation is Response,
        returns_none=return_annotation is None or return_annotation is type(None),
    )


def _call_values(
    effective: _EffectiveDeclaration,
    resolved: _ResolvedSignature,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    call_kwargs = dict(kwargs)
    implicit_options = inspect.Parameter.empty
    if "_options" not in resolved.signature.parameters:
        implicit_options = call_kwargs.pop("_options", inspect.Parameter.empty)
    binder = resolved.signature.bind
    if effective.declaration.has_self:
        bound = binder(None, *args, **call_kwargs)
    else:
        bound = binder(*args, **call_kwargs)
    values = dict(bound.arguments)
    values.pop("self", None)
    if implicit_options is not inspect.Parameter.empty:
        values["_options"] = implicit_options
    return values


def _wire_name(field_info: RapidyFieldInfo) -> str:
    alias = field_info.alias
    return alias if isinstance(alias, str) else field_info.name


def _has_marker_default(field_info: RapidyFieldInfo) -> bool:
    return field_info.default is not Undefined and field_info.default is not Required


def _is_json_content_type(content_type: object) -> bool:
    normalized = str(content_type).split(";", 1)[0].strip().lower()
    return normalized == "application/json" or normalized.endswith("+json")


def _unsupported_aggregate(kind: str) -> typing.NoReturn:
    raise SchemaDefinitionError(
        f"aggregate {kind} serialization is implemented in milestone 16"
    )


def _pick_option(options: CallOptions | None, name: str, declared: Any) -> Any:
    value = getattr(options, name) if options is not None else UNSET
    return declared if value is UNSET else value


def _dispatch(
    client: _ClientLike,
    effective: _EffectiveDeclaration,
    resolved: _ResolvedSignature,
    call_values: Mapping[str, Any],
) -> Any:
    from rapidy_client.schema import CallOptions, File, Form

    values = dict(call_values)
    options = values.pop("_options", None)
    if options is not None and not isinstance(options, CallOptions):
        raise TypeError("_options must be CallOptions or None")

    path_params: dict[str, Any] = {}
    query: dict[str, Any] = {}
    header_map: dict[str, str] = {}
    cookie_map: dict[str, str] = {}
    json_body: Any = None
    content_body: Any = None
    data_body: Any = None
    files_body: Any = None
    for data_attr in resolved.data_attrs:
        field_info = data_attr.field_info
        parameter_name = field_info.name
        if parameter_name in values:
            value = values[parameter_name]
        elif _has_marker_default(field_info):
            value = field_info.default
        else:
            continue

        wire_name = _wire_name(field_info)
        param_type = field_info.param_type
        if param_type is HTTPRequestParamType.path:
            path_params[parameter_name] = value
        elif param_type is HTTPRequestParamType.query:
            if not field_info.extract_single:
                _unsupported_aggregate("QueryParams")
            query[wire_name] = value
        elif param_type is HTTPRequestParamType.header:
            if not field_info.extract_single:
                _unsupported_aggregate("Headers")
            header_map[wire_name] = str(value)
        elif param_type is HTTPRequestParamType.cookie:
            if not field_info.extract_single:
                _unsupported_aggregate("Cookies")
            cookie_map[wire_name] = str(value)
        elif param_type is HTTPRequestParamType.body:
            if isinstance(field_info, Form):
                data_body = value
            elif isinstance(field_info, File):
                files_body = value
            elif _is_json_content_type(getattr(field_info, "content_type", None)):
                json_body = value
            else:
                content_body = value

    if cookie_map:
        header_map.setdefault(
            "Cookie", "; ".join(f"{key}={value}" for key, value in cookie_map.items())
        )
    if options is not None and options.headers:
        header_map.update(
            (str(key), str(value)) for key, value in options.headers.items()
        )

    request_kwargs = {
        "path_params": path_params or None,
        "query": query or None,
        "headers": header_map or None,
        "json": json_body,
        "content": content_body,
        "data": data_body,
        "files": files_body,
        "timeout": _pick_option(options, "timeout", effective.timeout),
        "retry": _pick_option(options, "retry", effective.retry),
        "auth": _pick_option(options, "auth", UNSET),
        "deadline": _pick_option(options, "deadline", effective.deadline),
        "follow_redirects": _pick_option(
            options, "follow_redirects", effective.follow_redirects
        ),
        "_declared_middlewares": effective.middlewares,
        "_endpoint": effective.full_path,
        "_idempotent": (
            None if effective.idempotent is UNSET else effective.idempotent
        ),
    }
    if resolved.returns_stream:
        return client.stream(
            effective.http_method, effective.full_path, **request_kwargs
        )

    async def invoke() -> Any:
        return await client.request(
            effective.http_method,
            effective.full_path,
            raise_for_status=False,
            **request_kwargs,
        )

    return invoke()


def _build_decorator(
    http_method: str,
    path: str,
    *,
    timeout: Timeout | float | None | Unset,
    retry: RetryConfig | None | Unset,
    deadline: float | Unset,
    follow_redirects: bool | Unset,
    idempotent: bool | Unset,
    statuses: Mapping[int, Any] | Unset,
    error_model: ErrorModel,
    query_serialization: QuerySerialization | Unset,
    middlewares: Sequence[Middleware] | Unset,
    name: str | Unset,
    serialization_options: Mapping[str, Any],
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorate(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        qualname = func.__qualname__
        _check_async(func, qualname)
        _check_empty_body(func, qualname)
        has_self, parameter_names, markers, deferred = _stage1_signature_scan(func)
        path_names = _path_param_names(path)
        _check_marking_and_paths(markers, path_names, qualname, deferred=deferred)
        _check_body_count(markers, qualname)
        _check_statuses_error_model_conflict(statuses, error_model, qualname)
        declaration = _EndpointDeclaration(
            http_method=http_method,
            path_template=path,
            func=func,
            qualname=qualname,
            has_self=has_self,
            path_param_names=path_names,
            signature_param_names=parameter_names,
            timeout=timeout,
            retry=retry,
            deadline=deadline,
            follow_redirects=follow_redirects,
            idempotent=idempotent,
            statuses=statuses,
            error_model=error_model,
            query_serialization=query_serialization,
            name=name,
            middlewares=() if middlewares is UNSET else tuple(middlewares),
            serialization_options=dict(serialization_options),
        )
        endpoint = Endpoint(_effective_functional(declaration))
        return cast(Callable[P, Awaitable[R]], endpoint)

    return decorate


def _method(
    http_method: str,
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    if "upstream" in serialization_options:
        raise TypeError("schema decorators do not accept client routing arguments")
    return _build_decorator(
        http_method,
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        serialization_options=serialization_options,
    )


def get(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "GET",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def post(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "POST",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def put(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "PUT",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def patch(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "PATCH",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def delete(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "DELETE",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def head(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "HEAD",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def options(
    path: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
    name: str | Unset = UNSET,
    **serialization_options: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return _method(
        "OPTIONS",
        path,
        timeout=timeout,
        retry=retry,
        deadline=deadline,
        follow_redirects=follow_redirects,
        idempotent=idempotent,
        statuses=statuses,
        error_model=error_model,
        query_serialization=query_serialization,
        middlewares=middlewares,
        name=name,
        **serialization_options,
    )


def controller(
    prefix: str,
    *,
    timeout: Timeout | float | None | Unset = UNSET,
    retry: RetryConfig | None | Unset = UNSET,
    deadline: float | Unset = UNSET,
    follow_redirects: bool | Unset = UNSET,
    idempotent: bool | Unset = UNSET,
    statuses: Mapping[int, Any] | Unset = UNSET,
    error_model: ErrorModel = UNSET,
    query_serialization: QuerySerialization | Unset = UNSET,
    middlewares: Sequence[Middleware] | Unset = UNSET,
) -> Callable[[C], C]:
    def decorate(cls: C) -> C:
        declaration = _ControllerDeclaration(
            prefix=prefix,
            cls_qualname=cls.__qualname__,
            timeout=timeout,
            retry=retry,
            deadline=deadline,
            follow_redirects=follow_redirects,
            idempotent=idempotent,
            statuses=statuses,
            error_model=error_model,
            query_serialization=query_serialization,
            middlewares=() if middlewares is UNSET else tuple(middlewares),
        )
        _check_statuses_error_model_conflict(statuses, error_model, cls.__qualname__)
        endpoints: dict[str, _EffectiveDeclaration] = {}
        for attribute_name, value in vars(cls).items():
            if not isinstance(value, Endpoint):
                continue
            method = value.declaration
            if not method.has_self:
                raise _schema_error(
                    method.qualname, "controller endpoint must have leading self"
                )
            effective = _effective_from_controller(declaration, method)
            _check_statuses_error_model_conflict(
                effective.statuses, effective.error_model, method.qualname
            )
            endpoints[attribute_name] = effective
            setattr(cls, attribute_name, _ControllerMethodDescriptor(attribute_name))
        if not endpoints:
            raise _schema_error(cls.__qualname__, "controller has no endpoints")
        cls.__rapidy_controller__ = declaration
        cls.__rapidy_endpoints__ = endpoints
        return cls

    return decorate


def bind(target: Any, client: _ClientLike) -> Any:
    if isinstance(target, Endpoint):
        return _BoundEndpoint(
            client, target._effective, _resolve_signature(target._effective)
        )
    if isinstance(target, type) and hasattr(target, "__rapidy_endpoints__"):
        instance = cast(Any, target).__new__(target)
        object.__setattr__(instance, "_rapidy_client", client)
        resolved = {
            name: _resolve_signature(effective)
            for name, effective in target.__rapidy_endpoints__.items()
        }
        object.__setattr__(instance, "_rapidy_bound", resolved)
        return instance
    raise TypeError("bind target must be an endpoint declaration or controller class")


__all__ = (
    "Stream",
    "bind",
    "controller",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
)
