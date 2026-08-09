from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rapidy.security.schemes import SecurityScheme

if TYPE_CHECKING:
    from rapidy.request import Request

__all__ = ('Guard', 'SecurityConfig', 'SecurityRequirements')

type GuardResult = bool | Awaitable[bool | None] | None
type Guard = Callable[[Request], GuardResult]
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


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    """Application security policy shared by runtime enforcement and OpenAPI generation."""

    schemes: Sequence[SecurityScheme] = field(default_factory=tuple)
    requirements: SecurityRequirements = field(default_factory=tuple)
    guards: Sequence[Guard] = field(default_factory=tuple)

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
        object.__setattr__(self, 'schemes', schemes)
        object.__setattr__(self, 'requirements', requirements)
        object.__setattr__(self, 'guards', tuple(self.guards))
