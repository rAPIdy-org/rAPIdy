from __future__ import annotations

import base64
import binascii
import hmac
import inspect
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from rapidy.request import Request
from rapidy.security.models import AuthCredentials, SecurityIdentity, SimpleUser

__all__ = (
    'APIKeyAuth',
    'AuthBackend',
    'AuthenticationError',
    'BasicAuth',
    'BearerAuth',
    'SecurityScheme',
    'constant_time_compare',
)

type AuthResult = SecurityIdentity | Any | None
type AuthVerifier = Callable[..., AuthResult | Awaitable[AuthResult]]

_SCHEME_NAME_PATTERN = re.compile(r'^[A-Za-z0-9._-]+$')


class AuthenticationError(Exception):
    """Signal that credentials were supplied but could not be authenticated."""


class AuthBackend(Protocol):
    """Authenticate one request without coupling the backend to routing or OpenAPI."""

    async def authenticate(self, request: Request) -> SecurityIdentity | None:
        """Return an identity, ``None`` for absent credentials, or raise AuthenticationError."""
        ...


class SecurityScheme:
    """Bind one runtime backend to its OpenAPI security-scheme definition."""

    __slots__ = ('backend', 'challenge', 'name', 'openapi_schema')

    def __init__(
        self,
        name: str,
        backend: AuthBackend,
        openapi_schema: Mapping[str, Any],
        *,
        challenge: str | None = None,
    ) -> None:
        if _SCHEME_NAME_PATTERN.fullmatch(name) is None:
            msg = 'Security scheme name may contain only letters, digits, `.`, `_`, and `-`'
            raise ValueError(msg)
        if challenge is not None and ('\r' in challenge or '\n' in challenge):
            msg = 'Security challenge must not contain newlines'
            raise ValueError(msg)
        self.name = name
        self.backend = backend
        self.openapi_schema = MappingProxyType(dict(openapi_schema))
        self.challenge = challenge

    async def authenticate(self, request: Request) -> SecurityIdentity | None:
        """Delegate authentication to the bound backend."""
        return await self.backend.authenticate(request)

    def __repr__(self) -> str:
        """Describe configuration without rendering callbacks or credential material."""
        return f'{type(self).__name__}(name={self.name!r}, backend={type(self.backend).__name__})'


def constant_time_compare(value: str | bytes, expected: str | bytes) -> bool:
    """Compare credential material without content-dependent early returns."""
    value_bytes = value.encode() if isinstance(value, str) else value
    expected_bytes = expected.encode() if isinstance(expected, str) else expected
    return hmac.compare_digest(value_bytes, expected_bytes)


async def _call_verifier(verifier: AuthVerifier, *args: str) -> AuthResult:
    result = verifier(*args)
    if inspect.isawaitable(result):
        return await result
    return result


def _identity(result: AuthResult, *, scheme: str, scopes: frozenset[str]) -> SecurityIdentity:
    if isinstance(result, SecurityIdentity):
        names = tuple(dict.fromkeys((*result.auth.schemes, scheme)))
        return SecurityIdentity(
            user=result.user,
            auth=AuthCredentials(scopes=result.auth.scopes | scopes, schemes=names),
        )
    return SecurityIdentity(user=result, auth=AuthCredentials(scopes=scopes, schemes=(scheme,)))


@dataclass(slots=True, repr=False)
class _BasicBackend:
    scheme: str
    scopes: frozenset[str]
    verify: AuthVerifier | None
    username: str | None
    password: str | None
    user: Any

    async def authenticate(self, request: Request) -> SecurityIdentity | None:
        authorization = request.headers.get('authorization')
        if authorization is None:
            return None
        prefix, separator, encoded = authorization.partition(' ')
        if not separator or prefix.lower() != 'basic' or not encoded:
            raise AuthenticationError
        try:
            decoded = base64.b64decode(encoded, validate=True).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise AuthenticationError from exc
        supplied_username, separator, supplied_password = decoded.partition(':')
        if not separator:
            raise AuthenticationError

        if self.verify is not None:
            result = await _call_verifier(self.verify, supplied_username, supplied_password)
        else:
            username_matches = constant_time_compare(supplied_username, self.username or '')
            password_matches = constant_time_compare(supplied_password, self.password or '')
            result = self.user if username_matches & password_matches else None
        if result is None:
            raise AuthenticationError
        return _identity(result, scheme=self.scheme, scopes=self.scopes)


class BasicAuth(SecurityScheme):
    """HTTP Basic authentication with either a verifier or constant-time static credentials."""

    def __init__(
        self,
        name: str = 'basicAuth',
        *,
        verify: AuthVerifier | None = None,
        username: str | None = None,
        password: str | None = None,
        user: Any = None,
        scopes: Sequence[str] = (),
        realm: str = 'rapidy',
        description: str | None = None,
    ) -> None:
        static_configured = username is not None or password is not None
        if (verify is None) == (not static_configured):
            msg = 'BasicAuth requires either `verify` or static `username` and `password`'
            raise ValueError(msg)
        if verify is None and (username is None or password is None):
            msg = 'BasicAuth static credentials require both `username` and `password`'
            raise ValueError(msg)
        if verify is not None and not callable(verify):
            msg = 'BasicAuth verify must be callable'
            raise TypeError(msg)
        if '"' in realm or '\r' in realm or '\n' in realm:
            msg = 'BasicAuth realm must not contain quotes or newlines'
            raise ValueError(msg)
        identity_user = user if user is not None else SimpleUser(username or 'basic')
        backend = _BasicBackend(name, frozenset(scopes), verify, username, password, identity_user)
        schema: dict[str, Any] = {'type': 'http', 'scheme': 'basic'}
        if description is not None:
            schema['description'] = description
        super().__init__(name, backend, schema, challenge=f'Basic realm="{realm}"')


@dataclass(slots=True, repr=False)
class _APIKeyBackend:
    scheme: str
    scopes: frozenset[str]
    location: str
    parameter_name: str
    key: str | None
    verify: AuthVerifier | None
    user: Any

    async def authenticate(self, request: Request) -> SecurityIdentity | None:
        if self.location == 'header':
            supplied = request.headers.get(self.parameter_name)
        elif self.location == 'query':
            supplied = request.query.get(self.parameter_name)
        else:
            supplied = request.cookies.get(self.parameter_name)
        if supplied is None:
            return None
        if self.verify is not None:
            result = await _call_verifier(self.verify, supplied)
        else:
            result = self.user if constant_time_compare(supplied, self.key or '') else None
        if result is None:
            raise AuthenticationError
        return _identity(result, scheme=self.scheme, scopes=self.scopes)


class APIKeyAuth(SecurityScheme):
    """Header, query, or cookie API-key authentication."""

    def __init__(
        self,
        name: str = 'apiKey',
        *,
        parameter_name: str = 'X-API-Key',
        location: str = 'header',
        key: str | None = None,
        verify: AuthVerifier | None = None,
        user: Any = None,
        scopes: Sequence[str] = (),
        description: str | None = None,
    ) -> None:
        if location not in {'header', 'query', 'cookie'}:
            msg = 'APIKeyAuth location must be `header`, `query`, or `cookie`'
            raise ValueError(msg)
        if not parameter_name:
            msg = 'APIKeyAuth parameter_name must not be empty'
            raise ValueError(msg)
        if (key is None) == (verify is None):
            msg = 'APIKeyAuth requires exactly one of `key` or `verify`'
            raise ValueError(msg)
        if key == '':
            msg = 'APIKeyAuth key must not be empty'
            raise ValueError(msg)
        if verify is not None and not callable(verify):
            msg = 'APIKeyAuth verify must be callable'
            raise TypeError(msg)
        identity_user = user if user is not None else SimpleUser(name)
        backend = _APIKeyBackend(
            name,
            frozenset(scopes),
            location,
            parameter_name,
            key,
            verify,
            identity_user,
        )
        schema: dict[str, Any] = {'type': 'apiKey', 'name': parameter_name, 'in': location}
        if description is not None:
            schema['description'] = description
        challenge = f'ApiKey realm="{name}"' if location == 'header' else None
        super().__init__(name, backend, schema, challenge=challenge)


@dataclass(slots=True, repr=False)
class _BearerBackend:
    scheme: str
    scopes: frozenset[str]
    verify: AuthVerifier

    async def authenticate(self, request: Request) -> SecurityIdentity | None:
        authorization = request.headers.get('authorization')
        if authorization is None:
            return None
        prefix, separator, token = authorization.partition(' ')
        if not separator or prefix.lower() != 'bearer' or not token:
            raise AuthenticationError
        result = await _call_verifier(self.verify, token)
        if result is None:
            raise AuthenticationError
        return _identity(result, scheme=self.scheme, scopes=self.scopes)


class BearerAuth(SecurityScheme):
    """Opaque Bearer-token authentication; token verification stays application-owned."""

    def __init__(
        self,
        verify: AuthVerifier,
        name: str = 'bearerAuth',
        *,
        scopes: Sequence[str] = (),
        bearer_format: str | None = None,
        description: str | None = None,
    ) -> None:
        if not callable(verify):
            msg = 'BearerAuth verify must be callable'
            raise TypeError(msg)
        backend = _BearerBackend(name, frozenset(scopes), verify)
        schema: dict[str, Any] = {'type': 'http', 'scheme': 'bearer'}
        if bearer_format is not None:
            schema['bearerFormat'] = bearer_format
        if description is not None:
            schema['description'] = description
        super().__init__(name, backend, schema, challenge='Bearer')
