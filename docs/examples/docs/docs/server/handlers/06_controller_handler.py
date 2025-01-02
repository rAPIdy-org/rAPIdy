from rapidy import Rapidy
from rapidy.http import PathParam, controller, get, post, put, patch, delete

@controller('/')
class UserController:
    @get('/{user_id}')
    async def get_by_id(self, user_id: str = PathParam()) -> dict[str, str]:
        return {'user_id': user_id}

    @get()
    async def get_all_users(self) -> list[dict[str, str]]:
        return [{'name': 'John'}, {'name': 'Felix'}]

    @post()
    async def create_user(self) -> str:
        return 'ok'

    @put()
    async def update_user(self) -> str:
        return 'ok'

    @patch()
    async def patch_user(self) -> str:
        return 'ok'

    @delete()
    async def delete_user(self) -> str:
        return 'ok'

rapidy = Rapidy(http_route_handlers=[UserController])
