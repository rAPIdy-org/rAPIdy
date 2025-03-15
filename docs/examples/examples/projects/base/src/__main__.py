import logging

from rapidy import run_app

from src.application import create_rapidy
from src.config import Config

if __name__ == "__main__":
    config = Config()

    logger = logging.getLogger(__name__)
    logger.setLevel(config.logger_level)

    rapidy = create_rapidy(logger=logger, config=config)

    run_app(
        rapidy,
        host=config.host,
        port=config.port,
    )
