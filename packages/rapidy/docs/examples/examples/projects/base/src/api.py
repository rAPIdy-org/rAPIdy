import logging

from dishka import FromDishka as Depends
from rapidy.http import get

from src.config import Config
from src.di import inject


@get("/")
@inject
async def handler(
    config: Depends[Config],
    logger: Depends[logging.Logger],
) -> dict[str, str]:
    logger.info("Hello rapidy")
    return {"hello": "rapidy", "app_name": config.app_name}
