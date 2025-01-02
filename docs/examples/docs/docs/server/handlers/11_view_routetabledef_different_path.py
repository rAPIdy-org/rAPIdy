from rapidy import web

routes = web.RouteTableDef()

@routes.view('/')
class Handler(web.View):
    @routes.get('/{user_id}')
    async def get(self, user_id: str = web.PathParam()) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def post(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def put(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def patch(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def delete(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

rapidy = web.Application()
rapidy.add_routes(routes)
