from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from rapidy.version import __version__

__all__ = ('OpenAPIConfig',)


def _default_servers() -> tuple[Mapping[str, Any], ...]:
    return ()


def _default_tags() -> tuple[Mapping[str, Any], ...]:
    return ()


def _default_security_schemes() -> Mapping[str, Mapping[str, Any]]:
    return {}


def _default_security() -> tuple[Mapping[str, Sequence[str]], ...]:
    return ()


@dataclass(frozen=True, slots=True)
class OpenAPIConfig:
    """Configure OpenAPI 3.1 schema generation and the bundled documentation routes."""

    title: str = 'rAPIdy'
    version: str = __version__
    description: str | None = None
    summary: str | None = None
    terms_of_service: str | None = None
    contact: Mapping[str, str] | None = None
    license: Mapping[str, str] | None = None
    servers: Sequence[Mapping[str, Any]] = field(default_factory=_default_servers)
    tags: Sequence[Mapping[str, Any]] = field(default_factory=_default_tags)
    security_schemes: Mapping[str, Mapping[str, Any]] = field(default_factory=_default_security_schemes)
    security: Sequence[Mapping[str, Sequence[str]]] = field(default_factory=_default_security)
    json_path: str = '/schema/openapi.json'
    swagger_path: str | None = '/schema'
    redoc_path: str | None = '/schema/redoc'

    def __post_init__(self) -> None:
        """Reject ambiguous documentation route configurations at application creation time."""
        if not self.title:
            msg = 'OpenAPI title must not be empty'
            raise ValueError(msg)
        if not self.version:
            msg = 'OpenAPI version must not be empty'
            raise ValueError(msg)

        paths = [self.json_path, self.swagger_path, self.redoc_path]
        enabled_paths = [path for path in paths if path is not None]
        for path in enabled_paths:
            if not path.startswith('/'):
                msg = f'OpenAPI route path must start with `/`: {path!r}'
                raise ValueError(msg)
            if path != '/' and path.endswith('/'):
                msg = f'OpenAPI route path must not end with `/`: {path!r}'
                raise ValueError(msg)
        if len(enabled_paths) != len(set(enabled_paths)):
            msg = 'OpenAPI route paths must be unique'
            raise ValueError(msg)
