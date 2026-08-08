from typing import Annotated

from rapidy import Rapidy
from rapidy.http import get, Header, HTTPRouter, PathParam, Request, Response
from rapidy.middlewares import middleware
from rapidy.typedefs import CallNext


@middleware(response_exclude_none=True)
async def require_token(
    request: Request,
    call_next: CallNext,
    token: Annotated[str, Header(alias='X-Token')],
) -> Response:
    """Validate a token and decorate the response."""
    request.state.token = token
    response = await call_next(request)
    response.headers['X-Authenticated'] = 'true'
    return response


@get('/items/{item_id}')
async def item(request: Request, item_id: Annotated[str, PathParam()]) -> dict[str, str]:
    """Read state written by middleware inside a mounted router."""
    return {'item': item_id, 'token': request.state.token}


api = HTTPRouter('/api', [item])
app = Rapidy(middlewares=[require_token], http_route_handlers=[api])
