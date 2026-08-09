from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from rapidy.version import __version__

if TYPE_CHECKING:
    from rapidy.openapi.plugins import OpenAPIRenderPlugin

__all__ = ('OpenAPIComponents', 'OpenAPIConfig')


def _default_servers() -> tuple[Mapping[str, Any], ...]:
    return ()


def _default_tags() -> tuple[Mapping[str, Any], ...]:
    return ()


def _default_security_schemes() -> Mapping[str, Mapping[str, Any]]:
    return {}


def _default_security() -> tuple[Mapping[str, Sequence[str]], ...]:
    return ()


def _default_webhooks() -> Mapping[str, Mapping[str, Any]]:
    return {}


def _default_component_objects() -> Mapping[str, Any]:
    return {}


def _validate_components(components: Any) -> None:
    if not isinstance(components, OpenAPIComponents):
        msg = 'OpenAPI components must be an OpenAPIComponents instance'
        raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class OpenAPIComponents:
    """Reusable OpenAPI 3.1 objects referenced by operations, callbacks, and webhooks."""

    schemas: Mapping[str, Any] = field(default_factory=_default_component_objects)
    responses: Mapping[str, Any] = field(default_factory=_default_component_objects)
    parameters: Mapping[str, Any] = field(default_factory=_default_component_objects)
    examples: Mapping[str, Any] = field(default_factory=_default_component_objects)
    request_bodies: Mapping[str, Any] = field(default_factory=_default_component_objects)
    headers: Mapping[str, Any] = field(default_factory=_default_component_objects)
    security_schemes: Mapping[str, Any] = field(default_factory=_default_component_objects)
    links: Mapping[str, Any] = field(default_factory=_default_component_objects)
    callbacks: Mapping[str, Any] = field(default_factory=_default_component_objects)
    path_items: Mapping[str, Any] = field(default_factory=_default_component_objects)


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
    components: OpenAPIComponents = field(default_factory=OpenAPIComponents)
    security_schemes: Mapping[str, Mapping[str, Any]] = field(default_factory=_default_security_schemes)
    security: Sequence[Mapping[str, Sequence[str]]] = field(default_factory=_default_security)
    webhooks: Mapping[str, Mapping[str, Any]] = field(default_factory=_default_webhooks)
    json_path: str = '/schema/openapi.json'
    swagger_path: str | None = '/schema'
    redoc_path: str | None = '/schema/redoc'
    render_plugins: Sequence[OpenAPIRenderPlugin] | None = None

    @classmethod
    def docs(cls, **config: Any) -> OpenAPIConfig:
        """Create the conventional opt-in ``/docs`` + ``/redoc`` preset."""
        return cls(
            json_path='/openapi.json',
            swagger_path='/docs',
            redoc_path='/redoc',
            **config,
        )

    def get_render_plugins(self) -> tuple[OpenAPIRenderPlugin, ...]:
        """Return explicit render plugins or the backward-compatible Swagger UI and ReDoc defaults."""
        if self.render_plugins is not None:
            return tuple(self.render_plugins)

        from rapidy.openapi.plugins import RedocRenderPlugin, SwaggerRenderPlugin  # noqa: PLC0415

        plugins: list[OpenAPIRenderPlugin] = []
        if self.swagger_path is not None:
            plugins.append(SwaggerRenderPlugin(path=self.swagger_path))
        if self.redoc_path is not None:
            plugins.append(RedocRenderPlugin(path=self.redoc_path))
        return tuple(plugins)

    def __post_init__(self) -> None:
        """Reject ambiguous documentation route configurations at application creation time."""
        if not self.title:
            msg = 'OpenAPI title must not be empty'
            raise ValueError(msg)
        if not self.version:
            msg = 'OpenAPI version must not be empty'
            raise ValueError(msg)
        _validate_components(self.components)
        if self.render_plugins is not None and (
            not isinstance(self.render_plugins, Sequence) or isinstance(self.render_plugins, (str, bytes, bytearray))
        ):
            msg = 'OpenAPI render plugins must be a sequence'
            raise ValueError(msg)
        if self.render_plugins is not None:
            object.__setattr__(self, 'render_plugins', tuple(self.render_plugins))

        configured_paths = [self.json_path, self.swagger_path, self.redoc_path]
        for path in (path for path in configured_paths if path is not None):
            if not path.startswith('/'):
                msg = f'OpenAPI route path must start with `/`: {path!r}'
                raise ValueError(msg)
            if path != '/' and path.endswith('/'):
                msg = f'OpenAPI route path must not end with `/`: {path!r}'
                raise ValueError(msg)
        from rapidy.openapi.plugins import OpenAPIRenderPlugin  # noqa: PLC0415

        plugins = self.get_render_plugins()
        if not all(isinstance(plugin, OpenAPIRenderPlugin) for plugin in plugins):
            msg = 'OpenAPI render plugins must inherit from OpenAPIRenderPlugin'
            raise ValueError(msg)
        enabled_paths = [self.json_path, *(plugin.path for plugin in plugins)]
        if len(enabled_paths) != len(set(enabled_paths)):
            msg = 'OpenAPI route paths must be unique'
            raise ValueError(msg)
