from __future__ import annotations

import asyncio
import json as _json
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from rapidy_core import UNSET, Unset

from rapidy_client._models import (
    BaseTransport,
    Headers,
    Request,
    Response,
    ResponseExtensions,
)
from rapidy_client.testing.chaos import ChaosServer

__all__ = (
    "ChaosServer",
    "FakeClock",
    "MockRouteError",
    "MockTransport",
    "RecordedCall",
)


class MockRouteError(Exception):
    """Raised when a request does not match a registered mock route."""

    def __init__(self, method: str, path: str, registered: Sequence[str]) -> None:
        self.method = method
        self.path = path
        self.registered = list(registered)
        listing = "\n".join(f"  - {signature}" for signature in registered)
        if not listing:
            listing = "  (no routes registered)"
        super().__init__(
            f"MockTransport: no route matched {method} {path}\n"
            f"registered routes:\n{listing}"
        )


@dataclass(frozen=True, slots=True)
class RecordedCall:
    """Immutable record of one request passing through ``MockTransport``."""

    request: Request
    response: Response | None = None
    exception: BaseException | None = None


class FakeClock:
    """Single-event-loop virtual clock that never performs a real delay."""

    __slots__ = ("_now",)

    def __init__(self, *, start: float = 0.0) -> None:
        self._now = start

    def monotonic(self) -> float:
        return self._now

    async def sleep(self, delay: float) -> None:
        if delay > 0.0:
            self._now += delay
        await asyncio.sleep(0)


type Handler = Callable[[Request], Awaitable[Response]]


async def _one_shot(body: bytes) -> AsyncIterator[bytes]:
    if body:
        yield body


@dataclass(slots=True)
class _ResponseSpec:
    status: int = 200
    json: Any | Unset = UNSET
    text: str | None = None
    content: bytes | None = None
    headers: Mapping[str, str] | None = None

    def build(self, request: Request) -> Response:
        content_type: str | None = None
        if self.json is not UNSET:
            body = _json.dumps(self.json).encode("utf-8")
            content_type = "application/json"
        elif self.text is not None:
            body = self.text.encode("utf-8")
        elif self.content is not None:
            body = self.content
        else:
            body = b""

        items = list((self.headers or {}).items())
        if content_type is not None and not any(
            name.casefold() == "content-type" for name, _ in items
        ):
            items.append(("content-type", content_type))

        extensions = ResponseExtensions(
            elapsed=0.0,
            attempt=request.extensions.attempt,
            connection_reused=None,
            pool_wait=None,
        )
        return Response(
            status=self.status,
            headers=Headers(items),
            request=request,
            extensions=extensions,
            stream=_one_shot(body),
            on_close=None,
            max_response_size=None,
        )


def _static_handler(spec: _ResponseSpec) -> Handler:
    async def _handler(request: Request) -> Response:
        return spec.build(request)

    return _handler


@dataclass(slots=True)
class _Step:
    count: int
    handler: Handler | None = None
    exc: BaseException | None = None


@dataclass(slots=True)
class _Route:
    method: str
    template: str
    pattern: re.Pattern[str]
    steps: list[_Step] = field(default_factory=list)
    _calls_seen: int = 0

    def select_step(self) -> _Step:
        call_index = self._calls_seen
        self._calls_seen += 1
        cumulative = 0
        for step in self.steps:
            cumulative += step.count
            if call_index < cumulative:
                return step
        return self.steps[-1]


def _compile_template(template: str) -> re.Pattern[str]:
    parts: list[str] = []
    for segment in re.split(r"(\{[^/}]+\})", template):
        if len(segment) >= 2 and segment[0] == "{" and segment[-1] == "}":
            parts.append(f"(?P<{segment[1:-1]}>[^/]+)")
        else:
            parts.append(re.escape(segment))
    return re.compile("".join(parts))


class _RouteBuilder:
    def __init__(self, route: _Route) -> None:
        self._route = route
        self._pending_times: int | None = None

    def times(self, n: int) -> _RouteBuilder:
        if n < 1:
            raise ValueError("times(n) requires n >= 1")
        self._pending_times = n
        return self

    def respond(
        self,
        *,
        status: int = 200,
        json: Any | Unset = UNSET,
        text: str | None = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> _RouteBuilder:
        spec = _ResponseSpec(
            status=status,
            json=json,
            text=text,
            content=content,
            headers=headers,
        )
        return self._append(handler=_static_handler(spec))

    def respond_with(self, handler: Handler) -> _RouteBuilder:
        return self._append(handler=handler)

    def raise_(self, exc: BaseException) -> _RouteBuilder:
        return self._append(exc=exc)

    def then(self) -> _RouteBuilder:
        return self

    def _append(
        self,
        *,
        handler: Handler | None = None,
        exc: BaseException | None = None,
    ) -> _RouteBuilder:
        count = 1 if self._pending_times is None else self._pending_times
        self._route.steps.append(_Step(count=count, handler=handler, exc=exc))
        self._pending_times = None
        return self


def _summary(calls: Sequence[RecordedCall]) -> list[str]:
    return [f"{call.request.method} {call.request.url.path}" for call in calls]


class MockTransport(BaseTransport):
    """Programmable in-memory transport for tests running in one event loop."""

    def __init__(self) -> None:
        self._routes: list[_Route] = []
        self.calls: list[RecordedCall] = []
        self.closed = False

    def route(self, method: str, path: str) -> _RouteBuilder:
        route = _Route(
            method=method.upper(),
            template=path,
            pattern=_compile_template(path),
        )
        self._routes.append(route)
        return _RouteBuilder(route)

    def _match(self, method: str, path: str) -> _Route | None:
        normalized_method = method.upper()
        for route in self._routes:
            if (
                route.method == normalized_method
                and route.pattern.fullmatch(path) is not None
            ):
                return route
        return None

    async def handle(self, request: Request) -> Response:
        route = self._match(request.method, request.url.path)
        if route is None:
            error = MockRouteError(
                request.method,
                request.url.path,
                [f"{item.method} {item.template}" for item in self._routes],
            )
            self.calls.append(RecordedCall(request=request, exception=error))
            raise error
        if not route.steps:
            raise RuntimeError(
                f"MockTransport: route {route.method} {route.template} has no outcome; "
                "call .respond()/.respond_with()/.raise_() on it"
            )

        step = route.select_step()
        if step.exc is not None:
            self.calls.append(RecordedCall(request=request, exception=step.exc))
            raise step.exc
        assert step.handler is not None
        response = await step.handler(request)
        self.calls.append(RecordedCall(request=request, response=response))
        return response

    async def aclose(self) -> None:
        self.closed = True

    def assert_called(
        self,
        method: str,
        path: str,
        *,
        times: int | None = None,
    ) -> None:
        normalized_method = method.upper()
        pattern = _compile_template(path)
        count = sum(
            1
            for call in self.calls
            if call.request.method.upper() == normalized_method
            and pattern.fullmatch(call.request.url.path) is not None
        )
        if times is None:
            if count == 0:
                raise AssertionError(
                    f"expected {method} {path} to be called at least once; "
                    f"recorded={_summary(self.calls)}"
                )
        elif count != times:
            raise AssertionError(
                f"expected {method} {path} called {times} time(s), got {count}; "
                f"recorded={_summary(self.calls)}"
            )
