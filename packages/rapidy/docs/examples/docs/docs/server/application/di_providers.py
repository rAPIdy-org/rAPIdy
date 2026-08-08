from typing import Annotated
from aiohttp.web import run_app
from rapidy import Rapidy
from rapidy.http import get
from rapidy.depends import provide, Provider, Scope, Resolve

class FooProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def c(self) -> int:
        return 1

@get('/')
async def handler(c: Annotated[int, Resolve()]) -> int:
    return c

app = Rapidy(
    http_route_handlers=[handler],
    di_providers=[FooProvider()],
)

if __name__ == '__main__':
    run_app(app)
