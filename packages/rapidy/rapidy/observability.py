from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from time import perf_counter_ns
from typing import Any, cast, Final

from rapidy_core.exceptions import RapidyException

from rapidy.application import Rapidy
from rapidy.typedefs import ASGIApp, ASGIMessage, ASGIScope, Receive, Send

__all__ = (
    'AccessLogMiddleware',
    'AccessLogRecord',
    'JSONAccessFormatter',
    'MissingOpenTelemetryDependencyError',
    'instrument_app',
)

_UNMATCHED_ROUTE: Final = '{unmatched}'
_TRACE_ID = re.compile(r'^[0-9a-f]{32}$')
_TRACEPARENT = re.compile(r'^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}(?:-.+)?$')
_LOGGER = logging.getLogger('rapidy.access')


@dataclass(frozen=True, slots=True)
class AccessLogRecord:
    """Low-cardinality request summary safe for structured production logs."""

    protocol: str
    method: str
    route: str
    status: int
    duration_ms: float
    request_size: int
    response_size: int
    request_id: str | None = None
    trace_id: str | None = None
    close_code: int | None = None

    def as_dict(self) -> dict[str, str | int | float | None]:
        """Return a serializer-ready mapping with stable field names."""
        return asdict(self)


class JSONAccessFormatter(logging.Formatter):
    """Serialize ``AccessLogMiddleware`` records as one compact JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        """Format access metadata and retain the human-readable event name."""
        access = getattr(record, 'rapidy_access', None)
        if not isinstance(access, Mapping):
            return super().format(record)
        document = {'event': record.getMessage(), **access}
        return json.dumps(document, separators=(',', ':'), sort_keys=True)


class AccessLogMiddleware:
    """ASGI middleware emitting one redacted structured record per HTTP or WebSocket exchange."""

    __slots__ = ('_app', '_clock', '_emit', '_logger')

    def __init__(
        self,
        app: ASGIApp,
        *,
        emit: Callable[[AccessLogRecord], None] | None = None,
        logger: logging.Logger | None = None,
        clock: Callable[[], int] = perf_counter_ns,
    ) -> None:
        self._app = app
        self._emit = emit
        self._logger = logger or _LOGGER
        self._clock = clock

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:  # noqa: C901
        """Proxy ASGI events and finalize at the protocol's terminal server event."""
        protocol = str(scope.get('type', ''))
        if protocol not in {'http', 'websocket'}:
            await self._app(scope, receive, send)
            return

        started_at = self._clock()
        request_size = 0
        response_size = 0
        content_length: int | None = None
        status = 500 if protocol == 'http' else 403
        close_code: int | None = None
        emitted = False

        async def tracked_receive() -> ASGIMessage:
            nonlocal request_size
            message = await receive()
            request_size += _message_size(message)
            return message

        async def tracked_send(message: ASGIMessage) -> None:
            nonlocal close_code, content_length, emitted, response_size, status
            message_type = message.get('type')
            if message_type == 'http.response.start':
                status = int(message.get('status', 500))
                content_length = _content_length(message.get('headers'))
            elif message_type in {'http.response.body', 'websocket.send'}:
                response_size += _message_size(message)
            elif message_type in {'http.response.pathsend', 'http.response.zerocopysend'}:
                count = message.get('count')
                response_size += int(count) if isinstance(count, int) else content_length or 0
            elif message_type == 'websocket.accept':
                status = 101
            elif message_type == 'websocket.close':
                close_code = int(message.get('code', 1000))
            await send(message)
            if not emitted and _is_terminal(message):
                emitted = True
                self._emit_record(
                    scope,
                    protocol=protocol,
                    status=status,
                    started_at=started_at,
                    request_size=request_size,
                    response_size=response_size,
                    close_code=close_code,
                )

        try:
            await self._app(scope, tracked_receive, tracked_send)
        finally:
            if not emitted:
                self._emit_record(
                    scope,
                    protocol=protocol,
                    status=status,
                    started_at=started_at,
                    request_size=request_size,
                    response_size=response_size,
                    close_code=close_code,
                )

    def _emit_record(
        self,
        scope: ASGIScope,
        *,
        protocol: str,
        status: int,
        started_at: int,
        request_size: int,
        response_size: int,
        close_code: int | None,
    ) -> None:
        state = scope.get('state')
        state_mapping = state if isinstance(state, Mapping) else {}
        record = AccessLogRecord(
            protocol=protocol,
            method=str(scope.get('method', 'WS')).upper() if protocol == 'http' else 'WS',
            route=str(scope.get('_rapidy_route_template', _UNMATCHED_ROUTE)),
            status=status,
            duration_ms=round((self._clock() - started_at) / 1_000_000, 3),
            request_size=request_size,
            response_size=response_size,
            request_id=_request_id(state_mapping),
            trace_id=_trace_id(scope),
            close_code=close_code,
        )
        try:
            if self._emit is not None:
                self._emit(record)
            else:
                self._logger.info('request.complete', extra={'rapidy_access': record.as_dict()})
        except Exception:
            self._logger.exception('Access log emitter failed')


class MissingOpenTelemetryDependencyError(RapidyException):
    """Raised when optional OpenTelemetry integration is requested without its extra."""

    message = 'OpenTelemetry integration requires `rapidy[otel]`.'


def instrument_app(
    app: Rapidy,
    *,
    tracer_provider: Any = None,
    meter_provider: Any = None,
    excluded_urls: str | None = None,
    server_request_hook: Callable[[Any, ASGIScope], None] | None = None,
) -> ASGIApp:
    """Wrap rAPIdy with official OpenTelemetry ASGI instrumentation using route templates."""
    try:
        from opentelemetry.instrumentation.asgi import (  # noqa: PLC0415
            OpenTelemetryMiddleware,
        )
    except ImportError as exc:
        raise MissingOpenTelemetryDependencyError from exc

    def span_details(scope: ASGIScope) -> tuple[str, dict[str, str]]:
        protocol = str(scope.get('type', 'http'))
        path = _application_path(scope)
        websocket = protocol == 'websocket'
        method = 'WS' if websocket else str(scope.get('method', 'HTTP')).upper()
        template = app.route_template(path, method=method, websocket=websocket)
        if template is None:
            return f'{method} {_UNMATCHED_ROUTE}', {}
        scope['_rapidy_route_template'] = template
        return f'{method} {template}', {'http.route': template}

    def request_hook(span: Any, scope: ASGIScope) -> None:
        span_context = span.get_span_context()
        trace_id = getattr(span_context, 'trace_id', 0)
        if isinstance(trace_id, int) and trace_id:
            scope['_rapidy_trace_id'] = f'{trace_id:032x}'
        if server_request_hook is not None:
            server_request_hook(span, scope)

    middleware = OpenTelemetryMiddleware(
        app,
        excluded_urls=excluded_urls,
        default_span_details=span_details,
        server_request_hook=request_hook,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        http_capture_headers_server_request=[],
        http_capture_headers_server_response=[],
    )
    return cast('ASGIApp', middleware)


def _message_size(message: Mapping[str, Any]) -> int:
    body = message.get('body')
    if isinstance(body, bytes):
        return len(body)
    frame = message.get('bytes')
    if isinstance(frame, bytes):
        return len(frame)
    text = message.get('text')
    return len(text.encode('utf-8')) if isinstance(text, str) else 0


def _content_length(raw_headers: Any) -> int | None:
    if not isinstance(raw_headers, list):
        return None
    for name, value in raw_headers:
        if bytes(name).lower() != b'content-length':
            continue
        try:
            return int(bytes(value))
        except (TypeError, ValueError):
            return None
    return None


def _is_terminal(message: Mapping[str, Any]) -> bool:
    message_type = message.get('type')
    if message_type in {'http.response.pathsend', 'websocket.close'}:
        return True
    return message_type in {'http.response.body', 'http.response.zerocopysend'} and not message.get(
        'more_body', False
    )


def _request_id(state: Mapping[str, Any]) -> str | None:
    value = state.get('request_id')
    return value if isinstance(value, str) else None


def _trace_id(scope: Mapping[str, Any]) -> str | None:
    explicit = scope.get('_rapidy_trace_id')
    if isinstance(explicit, str) and _TRACE_ID.fullmatch(explicit) and explicit != '0' * 32:
        return explicit
    raw_headers = scope.get('headers')
    if not isinstance(raw_headers, list):
        return None
    for name, value in raw_headers:
        if bytes(name).lower() != b'traceparent':
            continue
        match = _TRACEPARENT.fullmatch(bytes(value).decode('latin-1').lower())
        if match is not None and match[1] != '0' * 32:
            return match[1]
    return None


def _application_path(scope: Mapping[str, Any]) -> str:
    path = str(scope.get('path', '/'))
    root_path = str(scope.get('root_path', ''))
    if root_path and path.startswith(root_path):
        return path[len(root_path) :] or '/'
    return path
