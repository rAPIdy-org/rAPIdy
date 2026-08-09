from mypy.plugin import Plugin
from rapidy_core.mypy.plugin import RapidyPlugin


def plugin(_version: str) -> type[Plugin]:
    """Return the rAPIdy plugin class to mypy."""
    return RapidyPlugin
