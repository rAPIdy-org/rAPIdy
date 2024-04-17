from mypy.plugin import Plugin

from rapidy.mypy.plugin import RapidyPlugin


def plugin(version: str) -> type[Plugin]:
    return RapidyPlugin
