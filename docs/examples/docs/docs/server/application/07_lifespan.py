from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy

async def startup() -> None:
    print('startup')

async def shutdown() -> None:
    print('shutdown')

async def cleanup() -> None:
    print('cleanup')

@asynccontextmanager
async def bg_task() -> AsyncGenerator[None, None]:
    try:
        print('starting background task')
        yield
    finally:
        print('finishing background task')

rapidy = Rapidy(
    on_startup=[startup],
    on_shutdown=[shutdown],
    on_cleanup=[cleanup],
    lifespan=[bg_task()],
)