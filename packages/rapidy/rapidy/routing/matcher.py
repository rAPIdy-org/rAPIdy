from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast, NamedTuple

from rapidy_core.exceptions import RapidyException

from rapidy.exceptions import HTTPMethodNotAllowed, HTTPNotFound
from rapidy.typedefs import Handler, TerminalHandler

__all__ = ('RouteMatch', 'RouteRecord', 'UrlMatcher')


class RouteMatch(NamedTuple):
    """Resolved terminal plus the request-specific route data."""

    terminal: TerminalHandler
    path_params: dict[str, str]
    route_kwargs: dict[str, Any]


class RouteRecord(NamedTuple):
    """Public, deterministic route metadata for introspection."""

    path: str
    method: str
    route_kwargs: dict[str, Any]
    handler: Handler
    allow_head: bool
    is_auto_head: bool
    parameters: tuple[Any, ...] = ()


class DuplicateRouteError(RapidyException):
    """Raised when the same method/template pair is registered twice."""

    message = 'Route `{method} {path}` is already registered.'


class PathTemplateError(RapidyException):
    """Raised when a dynamic path template cannot be compiled safely."""

    message = 'Invalid path template `{path}`: {reason}'


@dataclass(slots=True)
class _RouteEntry:
    terminal: TerminalHandler
    route_kwargs: dict[str, Any]
    is_auto_head: bool


@dataclass(slots=True)
class _DynamicRoute:
    path: str
    pattern: re.Pattern[str]
    methods: dict[str, _RouteEntry]


@dataclass(slots=True)
class _WebSocketDynamicRoute:
    path: str
    pattern: re.Pattern[str]
    terminal: Handler
    route_kwargs: dict[str, Any]


def _find_parameter_end(path: str, start: int) -> int:
    depth = 1
    index = start + 1
    while index < len(path):
        character = path[index]
        if character == '\\':
            index += 2
            continue
        if character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _compile_path(path: str) -> re.Pattern[str] | None:  # noqa: C901
    if not path.startswith('/'):
        raise PathTemplateError(path=path, reason='path must start with `/`')

    chunks: list[str] = []
    names: set[str] = set()
    literal_start = 0
    index = 0
    dynamic = False

    while index < len(path):
        character = path[index]
        if character == '}':
            raise PathTemplateError(path=path, reason='unexpected closing brace')
        if character != '{':
            index += 1
            continue

        dynamic = True
        chunks.append(re.escape(path[literal_start:index]))
        end = _find_parameter_end(path, index)
        if end < 0:
            raise PathTemplateError(path=path, reason='unclosed path parameter')

        definition = path[index + 1 : end]
        name, separator, expression = definition.partition(':')
        if not name.isidentifier():
            raise PathTemplateError(path=path, reason=f'`{name}` is not a valid parameter name')
        if name in names:
            raise PathTemplateError(path=path, reason=f'parameter `{name}` is repeated')
        if separator and not expression:
            raise PathTemplateError(path=path, reason=f'parameter `{name}` has an empty regex')

        names.add(name)
        chunks.append(f'(?P<{name}>{expression if separator else "[^/]+"})')
        index = end + 1
        literal_start = index

    if not dynamic:
        return None

    chunks.append(re.escape(path[literal_start:]))
    try:
        return re.compile(''.join(chunks))
    except re.error as exc:
        raise PathTemplateError(path=path, reason=str(exc)) from exc


class UrlMatcher:
    """Static-first matcher with ordered dynamic candidates."""

    __slots__ = (
        '_dynamic',
        '_dynamic_by_path',
        '_prefixes',
        '_records',
        '_static',
        '_ws_dynamic',
        '_ws_dynamic_by_path',
        '_ws_static',
    )

    def __init__(self) -> None:
        self._static: dict[str, dict[str, _RouteEntry]] = {}
        self._dynamic: list[_DynamicRoute] = []
        self._dynamic_by_path: dict[str, _DynamicRoute] = {}
        self._records: list[RouteRecord] = []
        self._prefixes: list[tuple[str, Any]] = []
        self._ws_static: dict[str, tuple[Handler, dict[str, Any]]] = {}
        self._ws_dynamic: list[_WebSocketDynamicRoute] = []
        self._ws_dynamic_by_path: dict[str, _WebSocketDynamicRoute] = {}

    @property
    def routes(self) -> tuple[RouteRecord, ...]:
        """Return a registration-order snapshot for public introspection."""
        return tuple(self._records)

    def add_prefix(self, prefix: str, subapp: Any) -> None:
        """Store a mount target in longest-prefix-first order."""
        self._prefixes.append((prefix, subapp))
        self._prefixes.sort(key=lambda item: len(item[0]), reverse=True)
        # Delegation with a stripped path is owned by Rapidy._dispatch_terminal.

    def add_route(
        self,
        method: str,
        path: str,
        terminal: TerminalHandler,
        route_kwargs: dict[str, Any],
        *,
        allow_head: bool = True,
        handler: Handler | None = None,
        parameters: tuple[Any, ...] = (),
    ) -> None:
        """Compile and register one method/template pair."""
        method = method.upper()
        pattern = _compile_path(path)
        methods = self._get_or_create_methods(path, pattern)
        existing = methods.get(method)

        if existing is not None and not (method == 'HEAD' and existing.is_auto_head):
            raise DuplicateRouteError(method=method, path=path)
        if existing is not None:
            self._remove_auto_head_record(path)

        entry = _RouteEntry(terminal=terminal, route_kwargs=dict(route_kwargs), is_auto_head=False)
        methods[method] = entry
        self._records.append(
            self._make_record(
                path=path,
                method=method,
                route_kwargs=route_kwargs,
                terminal=terminal,
                handler=handler,
                allow_head=allow_head,
                is_auto_head=False,
                parameters=parameters,
            )
        )

        if method == 'GET' and allow_head and 'HEAD' not in methods:
            methods['HEAD'] = _RouteEntry(
                terminal=terminal,
                route_kwargs=dict(route_kwargs),
                is_auto_head=True,
            )
            self._records.append(
                self._make_record(
                    path=path,
                    method='HEAD',
                    route_kwargs=route_kwargs,
                    terminal=terminal,
                    handler=handler,
                    allow_head=allow_head,
                    is_auto_head=True,
                    parameters=parameters,
                )
            )

    def resolve(self, method: str, path: str) -> RouteMatch:
        """Resolve a request or raise a deterministic 404/405 error."""
        method = method.upper()
        allowed_methods: set[str] = set()

        static_methods = self._static.get(path)
        if static_methods is not None:
            entry = static_methods.get(method)
            if entry is not None:
                return self._to_match(entry, {}, path)
            allowed_methods.update(static_methods)

        for candidate in self._dynamic:
            match = candidate.pattern.fullmatch(path)
            if match is None:
                continue
            entry = candidate.methods.get(method)
            if entry is not None:
                return self._to_match(entry, match.groupdict(), candidate.path)
            allowed_methods.update(candidate.methods)

        if allowed_methods:
            raise HTTPMethodNotAllowed(method, allowed_methods)
        raise HTTPNotFound

    def add_ws_route(self, path: str, terminal: Handler, route_kwargs: dict[str, Any] | None = None) -> None:
        """Register a ``(WebSocket, Request) -> None`` terminal in the independent WS table."""
        metadata = dict(route_kwargs or {})
        pattern = _compile_path(path)
        if pattern is None:
            if path in self._ws_static:
                raise DuplicateRouteError(method='WS', path=path)
            self._ws_static[path] = (terminal, metadata)
            return

        if path in self._ws_dynamic_by_path:
            raise DuplicateRouteError(method='WS', path=path)
        candidate = _WebSocketDynamicRoute(path=path, pattern=pattern, terminal=terminal, route_kwargs=metadata)
        self._ws_dynamic_by_path[path] = candidate
        self._ws_dynamic.append(candidate)

    def resolve_ws(self, path: str) -> RouteMatch:
        """Resolve a WebSocket path without applying HTTP method semantics."""
        static_route = self._ws_static.get(path)
        if static_route is not None:
            terminal, route_kwargs = static_route
            return self._to_ws_match(terminal, route_kwargs, {}, path)

        for candidate in self._ws_dynamic:
            match = candidate.pattern.fullmatch(path)
            if match is not None:
                return self._to_ws_match(
                    candidate.terminal,
                    candidate.route_kwargs,
                    match.groupdict(),
                    candidate.path,
                )
        raise HTTPNotFound

    def route_template(self, path: str, *, websocket: bool = False) -> str | None:
        """Return the matching template independently of HTTP method semantics."""
        if websocket:
            if path in self._ws_static:
                return path
            for ws_candidate in self._ws_dynamic:
                if ws_candidate.pattern.fullmatch(path) is not None:
                    return ws_candidate.path
            return None
        if path in self._static:
            return path
        for http_candidate in self._dynamic:
            if http_candidate.pattern.fullmatch(path) is not None:
                return http_candidate.path
        return None

    def _get_or_create_methods(
        self,
        path: str,
        pattern: re.Pattern[str] | None,
    ) -> dict[str, _RouteEntry]:
        if pattern is None:
            return self._static.setdefault(path, {})

        candidate = self._dynamic_by_path.get(path)
        if candidate is None:
            candidate = _DynamicRoute(path=path, pattern=pattern, methods={})
            self._dynamic_by_path[path] = candidate
            self._dynamic.append(candidate)
        return candidate.methods

    @staticmethod
    def _make_record(
        *,
        path: str,
        method: str,
        route_kwargs: dict[str, Any],
        terminal: TerminalHandler,
        handler: Handler | None,
        allow_head: bool,
        is_auto_head: bool,
        parameters: tuple[Any, ...],
    ) -> RouteRecord:
        source_handler = handler if handler is not None else cast('Handler', getattr(terminal, '__wrapped__', terminal))
        return RouteRecord(
            path,
            method,
            dict(route_kwargs),
            source_handler,
            allow_head,
            is_auto_head,
            parameters,
        )

    def _remove_auto_head_record(self, path: str) -> None:
        self._records = [
            record
            for record in self._records
            if not (record.path == path and record.method == 'HEAD' and record.is_auto_head)
        ]

    @staticmethod
    def _to_match(entry: _RouteEntry, path_params: dict[str, str], template: str) -> RouteMatch:
        route_kwargs = dict(entry.route_kwargs)
        route_kwargs['_rapidy_route_template'] = template
        return RouteMatch(entry.terminal, path_params, route_kwargs)

    @staticmethod
    def _to_ws_match(
        terminal: Handler,
        route_kwargs: dict[str, Any],
        path_params: dict[str, str],
        template: str,
    ) -> RouteMatch:
        metadata = dict(route_kwargs)
        metadata['_rapidy_route_template'] = template
        return RouteMatch(cast('TerminalHandler', terminal), path_params, metadata)
