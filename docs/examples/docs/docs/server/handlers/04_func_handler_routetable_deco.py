from rapidy import web, Rapidy

routes = web.RouteTableDef()

@routes.post('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_routes(routes)