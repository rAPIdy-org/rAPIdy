from __future__ import annotations

import re
from collections.abc import Iterable
from re import Pattern
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ._utils import add_response_hook, append_vary, response_headers
from rapidy.response import Response

if TYPE_CHECKING:
    from multidict import CIMultiDict

    from rapidy.request import Request
    from rapidy.typedefs import CallNext, HTTPResponse

__all__ = ('CORSMiddleware',)

_ALL_METHODS = ('DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT')
_FIELD_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_FIRST_CONTROL_CODEPOINT = 32
_DELETE_CODEPOINT = 127


class CORSMiddleware:
    """Apply validated CORS, preflight, and Private Network Access policy."""

    __slots__ = (
        '_allow_all_headers',
        '_allow_all_origins',
        '_allow_credentials',
        '_allow_headers',
        '_allow_methods',
        '_allow_origins',
        '_allow_private_network',
        '_expose_headers',
        '_max_age',
        '_origin_regex',
    )

    def __init__(
        self,
        *,
        allow_origins: Iterable[str] = (),
        allow_origin_regex: str | Pattern[str] | None = None,
        allow_methods: Iterable[str] = ('GET',),
        allow_headers: Iterable[str] = (),
        expose_headers: Iterable[str] = (),
        allow_credentials: bool = False,
        allow_private_network: bool = False,
        max_age: int = 600,
    ) -> None:
        origins = tuple(dict.fromkeys(allow_origins))
        methods = tuple(dict.fromkeys(method.upper() for method in allow_methods))
        headers = tuple(dict.fromkeys(header.lower() for header in allow_headers))
        exposed = tuple(dict.fromkeys(expose_headers))
        if not methods:
            msg = 'allow_methods must contain at least one method'
            raise ValueError(msg)
        _validate_field_names(methods, option='allow_methods', allow_wildcard=True)
        if '*' in methods:
            methods = _ALL_METHODS
        _validate_field_names(headers, option='allow_headers', allow_wildcard=True)
        _validate_field_names(exposed, option='expose_headers', allow_wildcard=True)
        if max_age < 0:
            msg = 'max_age must be greater than or equal to zero'
            raise ValueError(msg)

        allow_all_origins = '*' in origins
        allow_all_headers = '*' in headers
        if allow_all_origins and len(origins) != 1:
            msg = "allow_origins='*' cannot be combined with explicit origins"
            raise ValueError(msg)
        for origin in origins:
            if origin != '*' and not _valid_origin(origin):
                msg = f'allow_origins contains an invalid serialized origin: {origin!r}'
                raise ValueError(msg)
        if allow_credentials and (allow_all_origins or allow_all_headers or '*' in exposed):
            msg = 'credentialed CORS cannot use wildcard origins, request headers, or exposed headers'
            raise ValueError(msg)

        self._allow_origins = frozenset(origins)
        self._allow_all_origins = allow_all_origins
        self._origin_regex = (
            re.compile(allow_origin_regex) if isinstance(allow_origin_regex, str) else allow_origin_regex
        )
        self._allow_methods = methods
        self._allow_headers = frozenset(headers)
        self._allow_all_headers = allow_all_headers
        self._expose_headers = exposed
        self._allow_credentials = allow_credentials
        self._allow_private_network = allow_private_network
        self._max_age = max_age

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Apply CORS policy around the next HTTP handler."""
        origin_values = request.headers.getall('origin', [])
        if not origin_values:
            return await call_next(request)
        origin = origin_values[0] if len(origin_values) == 1 and _valid_origin(origin_values[0]) else ''

        if _is_preflight(request):
            return self._preflight_response(request, origin)

        if origin and self._origin_is_allowed(origin):
            add_response_hook(request, lambda response: self._apply_simple_headers(response, origin))
        return await call_next(request)

    def _origin_is_allowed(self, origin: str) -> bool:
        if self._allow_all_origins or origin in self._allow_origins:
            return True
        return self._origin_regex is not None and self._origin_regex.fullmatch(origin) is not None

    def _apply_simple_headers(self, response: HTTPResponse, origin: str) -> None:
        headers = response_headers(response)
        self._apply_origin(headers, origin)
        if self._allow_credentials:
            headers['access-control-allow-credentials'] = 'true'
        if self._expose_headers:
            headers['access-control-expose-headers'] = ', '.join(self._expose_headers)

    def _preflight_response(self, request: Request, origin: str) -> Response:
        method_values = request.headers.getall('access-control-request-method', [])
        requested_method = method_values[0].upper() if len(method_values) == 1 else ''
        try:
            requested_headers = _requested_headers(
                ','.join(request.headers.getall('access-control-request-headers', []))
            )
        except ValueError:
            requested_headers = frozenset({'<invalid>'})
        private_network_values = request.headers.getall('access-control-request-private-network', [])
        private_network_requested = bool(private_network_values)
        private_network_valid = len(private_network_values) == 1 and private_network_values[0].lower() == 'true'
        origin_allowed = bool(origin) and self._origin_is_allowed(origin)
        method_allowed = requested_method in self._allow_methods
        headers_allowed = self._allow_all_headers or requested_headers.issubset(self._allow_headers)
        private_network_allowed = not private_network_requested or (
            private_network_valid and self._allow_private_network
        )
        allowed = origin_allowed and method_allowed and headers_allowed and private_network_allowed

        response = Response(
            None if allowed else 'CORS request denied',
            status=204 if allowed else 400,
            content_type=None if allowed else 'text/plain',
        )
        headers = response.headers
        append_vary(
            headers,
            'Origin',
            'Access-Control-Request-Method',
            'Access-Control-Request-Headers',
            'Access-Control-Request-Private-Network',
        )
        if origin_allowed:
            self._apply_origin(headers, origin)
        if self._allow_credentials:
            headers['access-control-allow-credentials'] = 'true'
        headers['access-control-allow-methods'] = ', '.join(self._allow_methods)
        if requested_headers and self._allow_all_headers and '<invalid>' not in requested_headers:
            headers['access-control-allow-headers'] = ', '.join(sorted(requested_headers))
        elif self._allow_headers:
            headers['access-control-allow-headers'] = ', '.join(sorted(self._allow_headers))
        if private_network_requested and self._allow_private_network:
            headers['access-control-allow-private-network'] = 'true'
        headers['access-control-max-age'] = str(self._max_age)
        return response

    def _apply_origin(self, headers: CIMultiDict[str], origin: str) -> None:
        if self._allow_all_origins:
            headers['access-control-allow-origin'] = '*'
            return
        headers['access-control-allow-origin'] = origin
        append_vary(headers, 'Origin')


def _is_preflight(request: Request) -> bool:
    return request.method == 'OPTIONS' and 'access-control-request-method' in request.headers


def _requested_headers(value: str) -> frozenset[str]:
    names = frozenset(item.strip().lower() for item in value.split(',') if item.strip())
    _validate_field_names(names, option='Access-Control-Request-Headers', allow_wildcard=False)
    return names


def _validate_field_names(names: Iterable[str], *, option: str, allow_wildcard: bool) -> None:
    for name in names:
        if allow_wildcard and name == '*':
            continue
        if not _FIELD_NAME.fullmatch(name):
            msg = f'{option} contains an invalid HTTP field name: {name!r}'
            raise ValueError(msg)


def _valid_origin(origin: str) -> bool:
    if origin == 'null':
        return True
    if not origin or any(
        character.isspace()
        or ord(character) < _FIRST_CONTROL_CODEPOINT
        or ord(character) == _DELETE_CODEPOINT
        for character in origin
    ):
        return False
    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    )
