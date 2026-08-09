from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import cast, TYPE_CHECKING
from urllib.parse import quote

from multidict import CIMultiDict, CIMultiDictProxy

if TYPE_CHECKING:
    from rapidy.request import Request
    from rapidy.typedefs import HTTPResponse

type ResponseHook = Callable[[HTTPResponse], HTTPResponse | Awaitable[HTTPResponse | None] | None]

_RESPONSE_HOOKS_KEY = '_rapidy_response_hooks'
_RESPONSE_HOOKS_APPLIED_KEY = '_rapidy_response_hooks_applied'


def add_response_hook(request: Request, hook: ResponseHook) -> None:
    """Register a response hook that also runs for framework-rendered errors."""
    hooks = cast('list[ResponseHook]', request.scope.setdefault(_RESPONSE_HOOKS_KEY, []))
    hooks.append(hook)


async def apply_response_hooks(request: Request, response: HTTPResponse) -> HTTPResponse:
    """Apply registered hooks in response/onion order."""
    applied = cast('set[int]', request.scope.setdefault(_RESPONSE_HOOKS_APPLIED_KEY, set()))
    if id(response) in applied:
        return response
    applied.add(id(response))
    hooks = cast('list[ResponseHook]', request.scope.get(_RESPONSE_HOOKS_KEY, []))
    current = response
    for hook in reversed(hooks):
        result = hook(current)
        if isawaitable(result):
            result = await result
        if result is not None:
            current = result
    applied.add(id(current))
    return current


def append_vary(headers: CIMultiDict[str], *names: str) -> None:
    """Append case-insensitive field names to ``Vary`` without duplicates."""
    existing_values = headers.getall('vary', [])
    if any(value.strip() == '*' for raw in existing_values for value in raw.split(',')):
        return
    values: list[str] = []
    seen: set[str] = set()
    for raw_value in existing_values:
        for value in raw_value.split(','):
            normalized = value.strip()
            if normalized and normalized.lower() not in seen:
                values.append(normalized)
                seen.add(normalized.lower())
    for name in names:
        if name.lower() not in seen:
            values.append(name)
            seen.add(name.lower())
    if values:
        headers['vary'] = ', '.join(values)


def replace_request_header(request: Request, name: str, value: str) -> None:
    """Replace one ASGI/request header while preserving all unrelated fields."""
    normalized = name.lower().encode('latin-1')
    raw_headers = [
        (bytes(key), bytes(item_value))
        for key, item_value in cast('list[tuple[bytes, bytes]]', request.scope.get('headers', []))
        if bytes(key).lower() != normalized
    ]
    raw_headers.append((normalized, value.encode('latin-1')))
    request.scope['headers'] = raw_headers
    request.headers = CIMultiDictProxy(
        CIMultiDict((key.decode('latin-1'), item_value.decode('latin-1')) for key, item_value in raw_headers)
    )


def external_path(request: Request) -> str:
    """Return the percent-preserving externally visible request path."""
    raw_path = request.scope.get('raw_path')
    if isinstance(raw_path, bytes):
        return raw_path.decode('latin-1')
    path = str(request.scope.get('path', '/'))
    return quote(path, safe="/%:@!$&'()*+,;=-._~")


def request_target(request: Request) -> str:
    """Return path and raw query suitable for redirects."""
    path = external_path(request)
    raw_query = request.scope.get('query_string', b'')
    if isinstance(raw_query, bytes) and raw_query:
        return f'{path}?{raw_query.decode("latin-1")}'
    return path


def response_headers(response: HTTPResponse) -> CIMultiDict[str]:
    """Return the shared mutable headers interface of every HTTP response."""
    return response.headers


def split_quoted(value: str, separator: str) -> list[str]:
    """Split one HTTP field while respecting quoted strings and escapes."""
    result: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif character == '\\' and quoted:
            current.append(character)
            escaped = True
        elif character == '"':
            current.append(character)
            quoted = not quoted
        elif character == separator and not quoted:
            result.append(''.join(current).strip())
            current = []
        else:
            current.append(character)
    result.append(''.join(current).strip())
    return result


def unquote_header_value(value: str) -> str:
    """Decode an RFC-style quoted field value without accepting bad framing."""
    if not value.startswith('"'):
        return value
    if value == '"' or not value.endswith('"'):
        return ''
    result: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            result.append(character)
            escaped = False
        elif character == '\\':
            escaped = True
        else:
            result.append(character)
    return '' if escaped else ''.join(result)
