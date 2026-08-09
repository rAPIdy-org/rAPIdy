from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = (
    'ANONYMOUS_AUTH',
    'ANONYMOUS_IDENTITY',
    'ANONYMOUS_USER',
    'AnonymousUser',
    'AuthCredentials',
    'SecurityIdentity',
    'SimpleUser',
)


@dataclass(frozen=True, slots=True)
class AuthCredentials:
    """Authenticated scheme names and authorization scopes, never raw credentials."""

    scopes: frozenset[str] = field(default_factory=frozenset)
    schemes: tuple[str, ...] = ()

    @property
    def scheme(self) -> str | None:
        """Return the primary authentication scheme, when one was used."""
        return self.schemes[0] if self.schemes else None

    def allows(self, *required_scopes: str) -> bool:
        """Return whether all requested scopes are present."""
        return self.scopes.issuperset(required_scopes)


@dataclass(frozen=True, slots=True)
class AnonymousUser:
    """Stable user object exposed before a request authenticates."""

    is_authenticated: bool = False
    display_name: str = ''


@dataclass(frozen=True, slots=True)
class SimpleUser:
    """Small built-in identity for applications that only need a string identifier."""

    username: str
    is_authenticated: bool = field(default=True, init=False)

    @property
    def display_name(self) -> str:
        """Return the username as a human-readable identity."""
        return self.username


ANONYMOUS_USER = AnonymousUser()
ANONYMOUS_AUTH = AuthCredentials()


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    """Typed DI value combining the current user and authorization credentials."""

    user: Any = ANONYMOUS_USER
    auth: AuthCredentials = ANONYMOUS_AUTH

    @property
    def is_authenticated(self) -> bool:
        """Return whether the identity was established by at least one scheme."""
        return bool(self.auth.schemes) and bool(getattr(self.user, 'is_authenticated', True))


ANONYMOUS_IDENTITY = SecurityIdentity()
