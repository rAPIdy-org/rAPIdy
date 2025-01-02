from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy

@asynccontextmanager
async def bg_task() -> AsyncGenerator[None, None]:
    try:
        print('starting background task')
        yield
    finally:
        print('finishing background task')

rapidy = Rapidy(
    lifespan=[bg_task()],
)