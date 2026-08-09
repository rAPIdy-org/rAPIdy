from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

from rapidy.openapi.ui import render_redoc, render_swagger_ui

if TYPE_CHECKING:
    from rapidy.request import Request

__all__ = ('OpenAPIRenderPlugin', 'RedocRenderPlugin', 'SwaggerRenderPlugin')


def _schema_title(openapi_schema: Mapping[str, Any]) -> str:
    info = openapi_schema.get('info')
    if isinstance(info, Mapping):
        title = info.get('title')
        if title is not None:
            return str(title)
    return 'OpenAPI'


def _validate_asset_url(value: str, *, name: str) -> None:
    if not value:
        msg = f'{name} must not be empty'
        raise ValueError(msg)


class OpenAPIRenderPlugin(ABC):
    """Render one OpenAPI representation at an application-relative path."""

    __slots__ = ('_media_type', '_path')

    def __init__(self, *, path: str, media_type: str = 'text/html') -> None:
        if not path.startswith('/'):
            msg = f'OpenAPI render plugin path must start with `/`: {path!r}'
            raise ValueError(msg)
        if path != '/' and path.endswith('/'):
            msg = f'OpenAPI render plugin path must not end with `/`: {path!r}'
            raise ValueError(msg)
        if not media_type:
            msg = 'OpenAPI render plugin media type must not be empty'
            raise ValueError(msg)
        self._path = path
        self._media_type = media_type

    @property
    def path(self) -> str:
        """Return the application-relative route that serves this representation."""
        return self._path

    @property
    def media_type(self) -> str:
        """Return the response media type for this representation."""
        return self._media_type

    @abstractmethod
    def render(
        self,
        request: Request,
        openapi_schema: Mapping[str, Any],
        *,
        schema_url: str,
    ) -> bytes:
        """Render this representation for one request."""


class SwaggerRenderPlugin(OpenAPIRenderPlugin):
    """Render Swagger UI with CDN, internal-host, or application-local assets."""

    __slots__ = ('css_url', 'init_oauth', 'js_url', 'options')

    def __init__(
        self,
        *,
        version: str = '5',
        js_url: str | None = None,
        css_url: str | None = None,
        options: Mapping[str, Any] | None = None,
        init_oauth: Mapping[str, Any] | None = None,
        path: str = '/schema',
        media_type: str = 'text/html',
    ) -> None:
        if js_url is None or css_url is None:
            _validate_asset_url(version, name='Swagger UI version')
        if js_url is not None:
            _validate_asset_url(js_url, name='Swagger UI JavaScript URL')
        if css_url is not None:
            _validate_asset_url(css_url, name='Swagger UI CSS URL')
        self.js_url = js_url or f'https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui-bundle.js'
        self.css_url = css_url or f'https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui.css'
        self.options = {'deepLinking': True, **dict(options or {})}
        self.init_oauth = dict(init_oauth) if init_oauth is not None else None
        super().__init__(path=path, media_type=media_type)

    def render(
        self,
        request: Request,
        openapi_schema: Mapping[str, Any],
        *,
        schema_url: str,
    ) -> bytes:
        """Render the configured Swagger UI document."""
        del request
        return render_swagger_ui(
            title=_schema_title(openapi_schema),
            schema_url=schema_url,
            js_url=self.js_url,
            css_url=self.css_url,
            options=self.options,
            init_oauth=self.init_oauth,
        ).encode()


class RedocRenderPlugin(OpenAPIRenderPlugin):
    """Render ReDoc with CDN, internal-host, or application-local assets."""

    __slots__ = ('js_url',)

    def __init__(
        self,
        *,
        version: str = '2',
        js_url: str | None = None,
        path: str = '/schema/redoc',
        media_type: str = 'text/html',
    ) -> None:
        if js_url is None:
            _validate_asset_url(version, name='ReDoc version')
        else:
            _validate_asset_url(js_url, name='ReDoc JavaScript URL')
        self.js_url = js_url or f'https://cdn.jsdelivr.net/npm/redoc@{version}/bundles/redoc.standalone.js'
        super().__init__(path=path, media_type=media_type)

    def render(
        self,
        request: Request,
        openapi_schema: Mapping[str, Any],
        *,
        schema_url: str,
    ) -> bytes:
        """Render the configured ReDoc document."""
        del request
        return render_redoc(
            title=_schema_title(openapi_schema),
            schema_url=schema_url,
            js_url=self.js_url,
        ).encode()
