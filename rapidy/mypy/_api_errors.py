from mypy.errorcodes import ErrorCode
from mypy.nodes import Context
from mypy.plugin import CheckerPluginInterface
from typing_extensions import Final

RAPIDY_NAME: Final[str] = 'rAPIdy'


ERROR_FIELD_DEFAULTS = ErrorCode('rapidy-param', 'Invalid Param defaults', RAPIDY_NAME)


def error_default_and_default_factory_specified(api: CheckerPluginInterface, context: Context) -> None:
    # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
    api.fail(
        '"default" and "default_factory" cannot be specified together for a requests parameter.',
        context,
        code=ERROR_FIELD_DEFAULTS,
    )


def error_default_or_default_factory_specified(api: CheckerPluginInterface, context: Context, param_name: str) -> None:
    api.fail(
        f'"default" or "default_factory" cannot be specified for "{param_name}"',
        context,
        code=ERROR_FIELD_DEFAULTS,
    )
