from rapidy import Rapidy
from rapidy.http import PathParam, controller, get

class UserController:
    @get('/{user_id}')
    async def get_by_id(self, user_id: str = PathParam()) -> dict[str, str]:
        return {'user_id': user_id}

    @get()
    async def get_all_users(self) -> list[dict[str, str]]:
        return [{'name': 'John'}, {'name': 'Felix'}]

rapidy = Rapidy(
    http_route_handlers=[
        controller.reg('/', UserController),
    ]
)
