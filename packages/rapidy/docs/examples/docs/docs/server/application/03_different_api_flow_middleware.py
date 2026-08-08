from rapidy import web
from rapidy.typedefs import Handler

routes = web.RouteTableDef()


def get_token_data(token: str) -> ...:
    ...


def get_session_data(session: str) -> ...:
    ...


@web.middleware
async def keycloak_auth_middleware(
        request: web.Request,
        handler: Handler,
        bearer_token: str = web.Header(alias='Authorization'),
) -> web.StreamResponse:
    try:
        parsed_token_data = get_token_data(bearer_token)
    except Exception:
        return web.HTTPUnauthorized(text='Failed to authenticate with bearer')

    return await handler(request)


@web.middleware
async def cookie_session_auth_middleware(
        request: web.Request,
        handler: Handler,
        session: str = web.Cookie(alias='UserSession'),
) -> web.StreamResponse:
    try:
        parsed_session_data = get_session_data(session)
    except Exception:
        return web.HTTPUnauthorized(text='Failed to authenticate with session')

    return await handler(request)


@routes.get('/get_hello')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}


v1_app = web.Application(middlewares=[cookie_session_auth_middleware])
v1_app.add_routes(routes)

v2_app = web.Application(middlewares=[keycloak_auth_middleware])
v2_app.add_routes(routes)

app = web.Application()
app.add_subapp('/v1', v1_app)
app.add_subapp('/v2', v2_app)