from typing import Type

from mypy.plugin import Plugin

from rapidy.mypy.plugin import RapidyPlugin


def plugin(version: str) -> Type[Plugin]:  # noqa: ARG001
    return RapidyPlugin
