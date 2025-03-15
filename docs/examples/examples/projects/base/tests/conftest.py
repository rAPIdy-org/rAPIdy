import logging
from typing import AsyncGenerator, Final

import pytest
from aiohttp.test_utils import BaseTestServer, TestServer, TestClient
from dishka import AsyncContainer
from rapidy import Rapidy

from src.application import create_rapidy, create_container
from src.config import Config

TEST_APP_NAME: Final[str] = 'Test APP'


@pytest.fixture
async def app_logger(app_config: Config) -> logging.Logger:
    return logging.getLogger()


@pytest.fixture
async def app_config() -> Config:
    return Config(
        app_name=TEST_APP_NAME,
    )


@pytest.fixture
async def app_container(
    app_config: Config,
    logger: logging.Logger,
) -> AsyncContainer:
    return create_container(
        config=app_config,
        logger=logger,
    )


@pytest.fixture
async def rapidy(app_config: Config, app_logger: logging.Logger) -> Rapidy:
    return create_rapidy(config=app_config, logger=app_logger)


@pytest.fixture
async def rapidy_server(rapidy: Rapidy) -> AsyncGenerator[BaseTestServer, None]:
    async with TestServer(rapidy) as server:
        yield server


@pytest.fixture
async def rapidy_client(rapidy_server: TestServer) -> AsyncGenerator[TestClient, None]:
    async with TestClient(rapidy_server) as client:
        yield client
