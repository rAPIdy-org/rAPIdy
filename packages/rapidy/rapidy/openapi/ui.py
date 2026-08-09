from __future__ import annotations

import html
import json

__all__ = ('render_redoc', 'render_swagger_ui')


def render_swagger_ui(*, title: str, schema_url: str) -> str:
    """Render a Swagger UI host page backed by the configured schema URL."""
    safe_title = html.escape(title)
    encoded_url = json.dumps(schema_url)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} — Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({{url: {encoded_url}, dom_id: '#swagger-ui', deepLinking: true}});
    </script>
  </body>
</html>
"""


def render_redoc(*, title: str, schema_url: str) -> str:
    """Render a ReDoc host page backed by the configured schema URL."""
    safe_title = html.escape(title)
    safe_url = html.escape(schema_url, quote=True)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} — ReDoc</title>
  </head>
  <body>
    <redoc spec-url="{safe_url}"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
  </body>
</html>
"""
