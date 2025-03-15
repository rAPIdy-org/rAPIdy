from rapidy import web

routes = web.RouteTableDef()

@routes.get('/get_hello')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

v1_app = web.Application()
v1_app.add_routes(routes)

app = web.Application()
app.add_subapp('/v1', v1_app)