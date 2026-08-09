from __future__ import annotations

import html
import json
from collections.abc import Mapping
from typing import Any

__all__ = ('render_redoc', 'render_swagger_ui')


def _script_json(value: Any) -> str:
    return (
        json.dumps(value, separators=(',', ':'), sort_keys=True)
        .replace('&', '\\u0026')
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
    )


def render_swagger_ui(
    *,
    title: str,
    schema_url: str,
    js_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js',
    css_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css',
    options: Mapping[str, Any] | None = None,
    init_oauth: Mapping[str, Any] | None = None,
) -> str:
    """Render a Swagger UI host page backed by the configured schema URL."""
    safe_title = html.escape(title)
    safe_js_url = html.escape(js_url, quote=True)
    safe_css_url = html.escape(css_url, quote=True)
    configured_options = dict(options or {})
    configured_options.update({'dom_id': '#swagger-ui', 'url': schema_url})
    encoded_options = _script_json(configured_options)
    oauth_initialization = f'\n      ui.initOAuth({_script_json(dict(init_oauth))});' if init_oauth is not None else ''
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} — Swagger UI</title>
    <link rel="stylesheet" href="{safe_css_url}">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="{safe_js_url}"></script>
    <script>
      const ui = SwaggerUIBundle({encoded_options});{oauth_initialization}
    </script>
  </body>
</html>
"""


def render_redoc(
    *,
    title: str,
    schema_url: str,
    js_url: str = 'https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js',
) -> str:
    """Render a ReDoc host page backed by the configured schema URL."""
    safe_title = html.escape(title)
    safe_url = html.escape(schema_url, quote=True)
    safe_js_url = html.escape(js_url, quote=True)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} — ReDoc</title>
  </head>
  <body>
    <redoc spec-url="{safe_url}"></redoc>
    <script src="{safe_js_url}"></script>
  </body>
</html>
"""
