from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field

from rapidy import request as _request
from rapidy._request_security import host_is_allowed, normalize_host_pattern, parse_host, valid_origin
from rapidy.security.schemes import SecurityScheme

__all__ = ('Guard', 'SecurityConfig', 'SecurityRequirements', 'WebSocketSecurityConfig')

type GuardResult = bool | Awaitable[bool | None] | None
type Guard = Callable[[_request.Request], GuardResult]
type SecurityRequirements = Sequence[Mapping[str, Sequence[str]]]


def _normalize_requirements(requirements: SecurityRequirements) -> tuple[dict[str, tuple[str, ...]], ...]:
    normalized: list[dict[str, tuple[str, ...]]] = []
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            msg = 'Each security requirement must be a mapping'
            raise TypeError(msg)
        normalized_requirement: dict[str, tuple[str, ...]] = {}
        for name, scopes in requirement.items():
            if not isinstance(name, str) or not name:
                msg = 'Security scheme references must be non-empty strings'
                raise ValueError(msg)
            if isinstance(scopes, (str, bytes, bytearray)) or not isinstance(scopes, Sequence):
                msg = f'Security scopes for {name!r} must be a sequence of strings'
                raise TypeError(msg)
            normalized_scopes = tuple(scopes)
            if not all(isinstance(scope, str) for scope in normalized_scopes):
                msg = f'Security scopes for {name!r} must be a sequence of strings'
                raise TypeError(msg)
            normalized_requirement[name] = normalized_scopes
        normalized.append(normalized_requirement)
    return tuple(normalized)


def _string_sequence(name: str, value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        msg = f'{name} must be a sequence of strings'
        raise TypeError(msg)
    if not all(isinstance(item, str) for item in value):
        msg = f'{name} must be a sequence of strings'
        raise TypeError(msg)
    return tuple(dict.fromkeys(value))


@dataclass(frozen=True, slots=True)
class WebSocketSecurityConfig:
    """Validate WebSocket Host and Origin headers before authentication or DI."""

    allowed_origins: Sequence[str] = field(default_factory=tuple)
    allowed_hosts: Sequence[str] = field(default_factory=tuple)
    allow_missing_origin: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.allow_missing_origin, bool):
            msg = 'allow_missing_origin must be a boolean'
            raise TypeError(msg)
        origins = _string_sequence('allowed_origins', self.allowed_origins)
        hosts = tuple(
            dict.fromkeys(
                normalize_host_pattern(host) for host in _string_sequence('allowed_hosts', self.allowed_hosts)
            )
        )
        if not origins and not hosts:
            msg = 'WebSocketSecurityConfig requires allowed_origins or allowed_hosts'
            raise ValueError(msg)
        if '*' in origins and len(origins) != 1:
            msg = "allowed_origins='*' cannot be combined with explicit origins"
            raise ValueError(msg)
        for origin in origins:
            if origin != '*' and not valid_origin(origin):
                msg = f'allowed_origins contains an invalid serialized origin: {origin!r}'
                raise ValueError(msg)
        if '*' in hosts and len(hosts) != 1:
            msg = "allowed_hosts='*' cannot be combined with explicit hosts"
            raise ValueError(msg)
        if self.allow_missing_origin and not origins:
            msg = 'allow_missing_origin requires an allowed_origins policy'
            raise ValueError(msg)
        object.__setattr__(self, 'allowed_origins', origins)
        object.__setattr__(self, 'allowed_hosts', hosts)

    @property
    def protects_ambient_credentials(self) -> bool:
        """Return whether the Origin policy is strict enough for cookie authentication."""
        return bool(self.allowed_origins) and not self.allow_missing_origin and not {
            '*',
            'null',
        }.intersection(self.allowed_origins)

    def accepts(self, request: _request.Request) -> bool:
        """Return whether one WebSocket handshake satisfies this policy."""
        if self.allowed_hosts:
            raw_hosts = request.headers.getall('host', [])
            host = parse_host(raw_hosts[0]) if len(raw_hosts) == 1 else None
            if host is None or not host_is_allowed(host, self.allowed_hosts):
                return False

        if not self.allowed_origins:
            return True
        raw_origins = request.headers.getall('origin', [])
        if not raw_origins:
            return self.allow_missing_origin
        if len(raw_origins) != 1 or not valid_origin(raw_origins[0]):
            return False
        return '*' in self.allowed_origins or raw_origins[0] in self.allowed_origins


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    """Application security policy shared by runtime enforcement and OpenAPI generation."""

    schemes: Sequence[SecurityScheme] = field(default_factory=tuple)
    requirements: SecurityRequirements = field(default_factory=tuple)
    guards: Sequence[Guard] = field(default_factory=tuple)
    websocket: WebSocketSecurityConfig | None = None

    @staticmethod
    def normalize_requirements(
        requirements: SecurityRequirements,
    ) -> tuple[dict[str, tuple[str, ...]], ...]:
        """Validate and freeze OpenAPI-shaped route or application requirements."""
        return _normalize_requirements(requirements)

    def __post_init__(self) -> None:
        schemes = tuple(self.schemes)
        names = [scheme.name for scheme in schemes]
        if len(names) != len(set(names)):
            msg = 'Security scheme names must be unique within one SecurityConfig'
            raise ValueError(msg)
        requirements = self.normalize_requirements(self.requirements)
        unknown = {name for requirement in requirements for name in requirement if name not in names}
        if unknown:
            msg = f'Unknown security schemes in requirements: {", ".join(sorted(unknown))}'
            raise ValueError(msg)
        if not all(callable(guard) for guard in self.guards):
            msg = 'Security guards must be callable'
            raise TypeError(msg)
        if self.websocket is not None and not isinstance(self.websocket, WebSocketSecurityConfig):
            msg = 'websocket must be a WebSocketSecurityConfig instance or None'
            raise TypeError(msg)
        object.__setattr__(self, 'schemes', schemes)
        object.__setattr__(self, 'requirements', requirements)
        object.__setattr__(self, 'guards', tuple(self.guards))
