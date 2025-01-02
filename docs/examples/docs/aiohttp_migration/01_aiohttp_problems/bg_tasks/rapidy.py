from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy

async def bg_task() -> None:
    print('run task')

@asynccontextmanager
async def app_ctx() -> AsyncGenerator[None, None]:
    print('starting background task')
    yield
    print('finishing background task')

rapidy = Rapidy(
    on_startup=[bg_task],
    on_shutdown=[bg_task],
    on_cleanup=[bg_task],
    lifespan=[app_ctx()],
)
# or
rapidy.lifespan.on_startup.append(bg_task)
rapidy.lifespan.on_shutdown.append(bg_task)
rapidy.lifespan.on_cleanup.append(bg_task)
rapidy.lifespan.append(app_ctx())