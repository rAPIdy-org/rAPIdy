from rapidy import web

routes = web.RouteTableDef()

class Handler(web.View):
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
rapidy.add_routes([
    web.get('/{user_id}', Handler),
    web.view('/', Handler),
])
