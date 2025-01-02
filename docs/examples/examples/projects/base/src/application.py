import logging

from dishka import AsyncContainer, make_async_container
from rapidy import Rapidy

from src.api import handler
from src.config import Config
from src.di import init_di_holder
from src.middlewares import error_catch_middleware
from src.providers import ConfigProvider, LoggerProvider


def create_container(
    config: Config,
    logger: logging.Logger,
) -> AsyncContainer:
    container = make_async_container(
        # providers
        ConfigProvider(),
        LoggerProvider(),
        # context
        context={
            Config: config,
            logging.Logger: logger,
        },
    )

    init_di_holder(container)

    return container


def create_rapidy(
    config: Config,
    logger: logging.Logger,
) -> Rapidy:
    create_container(config=config, logger=logger)

    return Rapidy(
        http_route_handlers=[
            handler,
        ],
        middlewares=[
            error_catch_middleware(logger=logger),
        ],
    )
