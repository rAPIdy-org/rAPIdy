from rapidy import Rapidy
from rapidy.http import get
from rapidy.depends import Depends, provide, Provider, Scope

class FooProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def c(self) -> int:
        return 1

@get('/')
async def handler(c: Depends[int]) -> dict:
    return {"value": c}

app = Rapidy(
    http_route_handlers=[handler],
    di_providers=[FooProvider()],
)