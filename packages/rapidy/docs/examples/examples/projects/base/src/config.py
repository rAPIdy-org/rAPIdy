from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH: Final[Path] = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    app_name: str = "src"

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 7000

    logger_level: str = "INFO"
    # projects env

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
