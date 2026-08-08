from rapidy import Rapidy
from rapidy.depends import make_async_container  # or: from dishka import make_async_container
from .providers import FooProvider

container = make_async_container(FooProvider())

async def shutdown_di_container() -> None:
    await container.close()

app = Rapidy(
   di_container=container,
   http_route_handlers=[...],
   on_shutdown=[shutdown_di_container],  # manual shutdown
)