from rapidy import web

routes = web.RouteTableDef()

@routes.get('/{user_id}')
async def handler(
        user_id: int = web.PathParam(),
        host: str = web.Header(alias='Host'),
        session: str = web.Cookie(alias='UserSession'),
        age_filter: str = web.QueryParam(alias='AgeFilter'),
        data: str = web.Body(),
) -> ...: