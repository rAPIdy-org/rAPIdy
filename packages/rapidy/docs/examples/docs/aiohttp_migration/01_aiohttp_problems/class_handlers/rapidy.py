from rapidy import Rapidy
from rapidy.http import controller, get, PathParam

@controller('/user')
class UserController:
    @get('/{user_id}')
    async def get_by_id(self, user_id: str = PathParam()) -> dict[str, str]:
        return {'user_id': user_id}

    @get()
    async def get_all_users(self) -> list[dict[str, str]]:
        return [{'user_id': '1'}, {'user_id': '2'}]

rapidy = Rapidy(http_route_handlers=[UserController])