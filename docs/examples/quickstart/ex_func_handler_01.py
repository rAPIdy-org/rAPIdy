from rapidy import web

routes = web.RouteTableDef()

@routes.post('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

app = web.Application()
app.add_routes(routes)
