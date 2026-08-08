import logging

from dishka import from_context, Provider, Scope

from src.config import Config


class ConfigProvider(Provider):
    scope = Scope.APP
    config = from_context(provides=Config)


class LoggerProvider(Provider):
    scope = Scope.APP
    config = from_context(provides=logging.Logger)
