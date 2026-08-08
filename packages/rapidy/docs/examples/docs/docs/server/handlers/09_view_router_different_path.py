from rapidy import Rapidy
from rapidy.web import View, PathParam

class Handler(View):
    async def get(self, user_id: str = PathParam()) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def post(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def put(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def patch(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def delete(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.router.add_get('/{user_id}', Handler)
rapidy.router.add_view('/', Handler)