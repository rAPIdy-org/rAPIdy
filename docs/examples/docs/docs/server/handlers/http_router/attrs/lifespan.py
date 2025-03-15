from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy
from rapidy.http import HTTPRouter

@asynccontextmanager
async def bg_task(rapidy: Rapidy) -> AsyncGenerator[None, None]:
    try:
        print('starting background task')
        yield
    finally:
        print('finishing background task')

router = HTTPRouter(
    path='/api',
    lifespan=[bg_task],
)