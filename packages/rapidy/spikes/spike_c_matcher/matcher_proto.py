from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, NamedTuple


class RouteMatch(NamedTuple):
    terminal: Any
    path_params: dict[str, str]
    route_kwargs: dict[str, Any]


class NotFound(Exception):
    pass


class MethodNotAllowed(Exception):
    def __init__(self, method: str, allowed_methods: set[str]) -> None:
        self.method = method
        self.allowed_methods = tuple(sorted(allowed_methods))
        super().__init__(method, self.allowed_methods)


@dataclass
class _Resource:
    path: str
    pattern: re.Pattern[str] | None
    methods: dict[str, tuple[Any, dict[str, Any]]]

    def match(self, path: str) -> dict[str, str] | None:
        if self.pattern is None:
            return {} if path == self.path else None
        match = self.pattern.fullmatch(path)
        return match.groupdict() if match is not None else None


class UrlMatcher:
    _parameter = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::(.+?))?\}")

    def __init__(self) -> None:
        self._static: dict[str, _Resource] = {}
        self._dynamic: list[_Resource] = []

    def add_route(
        self,
        method: str,
        path: str,
        terminal: Any,
        route_kwargs: dict[str, Any] | None = None,
        *,
        allow_head: bool = True,
    ) -> None:
        if not path.startswith("/"):
            raise ValueError("Route path must start with '/'.")
        method = method.upper()
        resource = self._find_resource(path)
        if resource is None:
            pattern = self._compile(path)
            resource = _Resource(path, pattern, {})
            if pattern is None:
                self._static[path] = resource
            else:
                self._dynamic.append(resource)
        if method in resource.methods:
            raise ValueError(f"Duplicate route: {method} {path}")
        value = (terminal, dict(route_kwargs or {}))
        resource.methods[method] = value
        if method == "GET" and allow_head and "HEAD" not in resource.methods:
            resource.methods["HEAD"] = value

    def resolve(self, method: str, path: str) -> RouteMatch:
        method = method.upper()
        static = self._static.get(path)
        if static is not None:
            return self._resolve_resource(static, method, {})

        allowed: set[str] = set()
        for resource in self._dynamic:
            parameters = resource.match(path)
            if parameters is None:
                continue
            value = resource.methods.get(method)
            if value is not None:
                terminal, route_kwargs = value
                return RouteMatch(terminal, parameters, dict(route_kwargs))
            allowed.update(resource.methods)
        if allowed:
            raise MethodNotAllowed(method, allowed)
        raise NotFound(path)

    def _resolve_resource(
        self, resource: _Resource, method: str, parameters: dict[str, str]
    ) -> RouteMatch:
        value = resource.methods.get(method)
        if value is None:
            raise MethodNotAllowed(method, set(resource.methods))
        terminal, route_kwargs = value
        return RouteMatch(terminal, parameters, dict(route_kwargs))

    def _find_resource(self, path: str) -> _Resource | None:
        if path in self._static:
            return self._static[path]
        return next(
            (resource for resource in self._dynamic if resource.path == path), None
        )

    @classmethod
    def _compile(cls, path: str) -> re.Pattern[str] | None:
        cursor = 0
        chunks: list[str] = []
        dynamic = False
        for match in cls._parameter.finditer(path):
            dynamic = True
            chunks.append(re.escape(path[cursor : match.start()]))
            name, expression = match.groups()
            chunks.append(f"(?P<{name}>{expression or '[^/]+'})")
            cursor = match.end()
        if not dynamic:
            return None
        chunks.append(re.escape(path[cursor:]))
        return re.compile("".join(chunks))


__all__ = ("MethodNotAllowed", "NotFound", "RouteMatch", "UrlMatcher")
