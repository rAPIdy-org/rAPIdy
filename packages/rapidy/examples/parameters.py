from typing import Annotated

from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, Cookie, Header, PathParam, post, QueryParam


class UserPatch(BaseModel):
    """Validated JSON patch."""

    display_name: str


@post('/users/{user_id}')
async def update_user(
    payload: Annotated[UserPatch, Body()],
    user_id: Annotated[int, PathParam()],
    token: Annotated[str, Header(alias='X-Token')],
    page: Annotated[int, QueryParam(alias='page')],
    session: Annotated[str, Cookie()],
) -> dict[str, object]:
    """Extract and return all supported request sources."""
    return {
        'user_id': user_id,
        'display_name': payload.display_name,
        'token': token,
        'page': page,
        'session': session,
    }


app = Rapidy(http_route_handlers=[update_user])
