from rapidy import Rapidy
from rapidy.http import controller, get
from rapidy.depends import Depends
from .providers import FooProvider

@controller('/')
class MyController:
    @get()
    async def handler(self, c: Depends[int]) -> dict:
        return {"value": c}

app = Rapidy(http_route_handlers=[MyController], di_providers=[FooProvider()])