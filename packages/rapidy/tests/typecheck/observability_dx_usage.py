from __future__ import annotations

from typing import Annotated

from rapidy import Rapidy
from rapidy.exceptions import HTTPException
from rapidy.http import get, PathParam, Request
from rapidy.observability import AccessLogMiddleware, AccessLogRecord, instrument_app
from rapidy.openapi import OpenAPIConfig
from rapidy.problems import ProblemDetailsRenderer
from rapidy.routing import URLPath
from rapidy.typedefs import ASGIApp


@get('/users/{user_id:\\d+}', name='user.detail')
async def user(request: Request, user_id: Annotated[int, PathParam()]) -> dict[str, str]:
    path: URLPath = request.url_for('user.detail', user_id=user_id)
    return {'self': path}


app = Rapidy(
    http_route_handlers=[user],
    exception_handlers={HTTPException: ProblemDetailsRenderer()},
    openapi_config=OpenAPIConfig.docs(title='Typed API', version='1'),
)
generated: URLPath = app.url_for('user.detail', user_id=1)
records: list[AccessLogRecord] = []
logged: ASGIApp = AccessLogMiddleware(app, emit=records.append)
traced: ASGIApp = instrument_app(app)
