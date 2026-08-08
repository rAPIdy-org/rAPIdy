from typing import AsyncGenerator
from aiohttp import web

async def bg_task(app: web.Application) -> None:
    print('run task')

async def app_ctx(app: web.Application) -> AsyncGenerator[None, None]:
    print('starting background task')
    yield
    print('finish')

app = web.Application()

app.on_startup.append(bg_task)
app.on_shutdown.append(bg_task)
app.on_cleanup.append(bg_task)
app.cleanup_ctx.append(app_ctx)