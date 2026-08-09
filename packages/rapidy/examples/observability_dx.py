from __future__ import annotations

from rapidy import Rapidy
from rapidy.http import get, PathParam, Request
from rapidy.observability import AccessLogMiddleware
from rapidy.openapi import OpenAPIConfig
from rapidy.problems import ProblemDetailsRenderer


class ItemNotFoundError(Exception):
    """Example domain error rendered without exposing internal details."""


@get('/items/{item_id:\\d+}', name='item.detail')
async def item(request: Request, item_id: int = PathParam()) -> dict[str, int | str]:
    """Return an item together with its generated canonical URL."""
    if item_id == 0:
        raise ItemNotFoundError
    return {
        'id': item_id,
        'self': request.url_for('item.detail', item_id=item_id),
    }


rapidy_app = Rapidy(
    http_route_handlers=[item],
    exception_handlers={ItemNotFoundError: ProblemDetailsRenderer()},
    openapi_config=OpenAPIConfig.docs(title='Items API', version='1.0.0'),
)

# Keep ``rapidy_app`` available for ``rapidy routes`` and expose the wrapped ASGI target to the server.
app = AccessLogMiddleware(rapidy_app)
