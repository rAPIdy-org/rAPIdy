from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ._utils import request_target
from rapidy.response import Response

if TYPE_CHECKING:
    from rapidy.request import Request
    from rapidy.typedefs import CallNext, HTTPResponse

__all__ = ('HTTPSRedirectMiddleware', 'TrustedHostMiddleware')


class TrustedHostMiddleware:
    """Reject requests whose authority is not in a validated host allowlist."""

    __slots__ = ('_allow_any', '_allowed_hosts', '_www_redirect')

    def __init__(self, allowed_hosts: Iterable[str], *, www_redirect: bool = True) -> None:
        patterns = tuple(dict.fromkeys(_normalize_pattern(pattern) for pattern in allowed_hosts))
        if not patterns:
            msg = 'allowed_hosts must contain at least one host pattern'
            raise ValueError(msg)
        if '*' in patterns and len(patterns) != 1:
            msg = "allowed_hosts='*' cannot be combined with explicit hosts"
            raise ValueError(msg)
        self._allowed_hosts = patterns
        self._allow_any = patterns == ('*',)
        self._www_redirect = www_redirect

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Validate the authority before dispatching the request."""
        if self._allow_any:
            return await call_next(request)
        raw_hosts = request.headers.getall('host', [])
        host = _parse_host(raw_hosts[0]) if len(raw_hosts) == 1 else None
        if host is not None and self._host_is_allowed(host):
            return await call_next(request)
        if host is not None and self._www_redirect and self._host_is_allowed(f'www.{host}'):
            scheme = str(request.scope.get('scheme', 'http'))
            authority = _www_authority(raw_hosts[0], host)
            return Response(
                status=307,
                headers={'location': f'{scheme}://{authority}{request_target(request)}'},
            )
        return Response('Invalid host header', status=400, content_type='text/plain')

    def _host_is_allowed(self, host: str) -> bool:
        return any(
            host == pattern or (pattern.startswith('*.') and host.endswith(pattern[1:]))
            for pattern in self._allowed_hosts
        )


class HTTPSRedirectMiddleware:
    """Redirect plaintext HTTP requests to the equivalent HTTPS URL."""

    __slots__ = ('_status',)

    def __init__(self, *, status: int = 307) -> None:
        if status not in (301, 302, 307, 308):
            msg = 'HTTPS redirect status must be one of 301, 302, 307, or 308'
            raise ValueError(msg)
        self._status = status

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Redirect HTTP or dispatch an already secure request."""
        if str(request.scope.get('scheme', 'http')).lower() != 'http':
            return await call_next(request)
        raw_hosts = request.headers.getall('host', [])
        if len(raw_hosts) != 1 or _parse_host(raw_hosts[0]) is None:
            return Response('Invalid host header', status=400, content_type='text/plain')
        return Response(
            status=self._status,
            headers={'location': f'https://{raw_hosts[0]}{request_target(request)}'},
        )


def _normalize_pattern(pattern: str) -> str:
    normalized = pattern.rstrip('.').lower()
    if normalized == '*':
        return normalized
    if not normalized or '/' in normalized or '@' in normalized or ':' in normalized:
        msg = f'Invalid trusted host pattern: {pattern!r}'
        raise ValueError(msg)
    if '*' in normalized and (not normalized.startswith('*.') or normalized.count('*') != 1):
        msg = f'Wildcard host patterns must start with "*.": {pattern!r}'
        raise ValueError(msg)
    candidate = normalized.removeprefix('*.')
    try:
        ascii_candidate = candidate.encode('idna').decode('ascii')
    except UnicodeError as exc:
        msg = f'Invalid trusted host pattern: {pattern!r}'
        raise ValueError(msg) from exc
    return f'*.{ascii_candidate}' if normalized.startswith('*.') else ascii_candidate


def _parse_host(value: str) -> str | None:
    if not value or any(character in value for character in '/?#@'):
        return None
    try:
        parsed = urlsplit(f'//{value}')
        host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return None
    if host is None:
        return None
    try:
        return host.rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError:
        return None


def _www_authority(raw_authority: str, host: str) -> str:
    parsed = urlsplit(f'//{raw_authority}')
    port = f':{parsed.port}' if parsed.port is not None else ''
    return f'www.{host}{port}'
