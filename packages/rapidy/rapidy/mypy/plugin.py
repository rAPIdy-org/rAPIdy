from typing import Callable, cast

from mypy.nodes import EllipsisExpr
from mypy.plugin import FunctionContext, Plugin
from mypy.types import CallableType, Overloaded, Type, TypeVarType

from pydantic.mypy import MYPY_VERSION_TUPLE

from rapidy.mypy._api_errors import (
    error_default_and_default_factory_specified,
    error_default_or_default_factory_specified,
)
from rapidy.mypy._type_helpers import _name_is_rapidy_param_name, _param_can_default, AnyTypeExplicit


class RapidyPlugin(Plugin):
    """A mypy plugin for processing Rapidy-specific parameter types and validations."""

    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
        """Retrieves a function hook for a given fully qualified function name.

        Args:
            fullname (str): The fully qualified function name.

        Returns:
            Optional[Callable[[FunctionContext], Type]]: A callback function if the function matches
            a Rapidy parameter, otherwise None.
        """
        sym = self.lookup_fully_qualified(fullname)
        if sym and _name_is_rapidy_param_name(cast(str, sym.fullname)):
            return self._rapidy_param_callback
        return None

    def _rapidy_param_callback(self, ctx: FunctionContext) -> Type:  # noqa: C901
        """Processes Rapidy parameter validation in a function call.

        This function ensures that parameters are correctly defined, handling constraints such as
        the mutual exclusivity of `default` and `default_factory` parameters.

        Args:
            ctx (FunctionContext): The context of the function call in mypy's type-checking.

        Returns:
            Type: The determined type of the parameter based on mypy's type system.
        """
        # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
        default_any_type = AnyTypeExplicit

        assert ctx.callee_arg_names[0] == 'default', '`default` is no longer first argument in ParamFieldInfo()'
        assert (
            ctx.callee_arg_names[1] == 'default_factory'
        ), '`default_factory` is no longer second argument in ParamFieldInfo()'

        default_args, default_factory_args = ctx.args[0], ctx.args[1]

        param_name = str(ctx.default_return_type)

        if default_args or default_factory_args:  # noqa: SIM102
            if not _param_can_default(param_name):
                error_default_or_default_factory_specified(ctx.api, ctx.context, param_name)
                return default_any_type

        if default_args and default_factory_args:
            error_default_and_default_factory_specified(ctx.api, ctx.context)
            return default_any_type

        if default_args:
            default_type = ctx.arg_types[0][0]
            default_arg = default_args[0]

            # Fallback to default Any type if the Param is required
            if not isinstance(default_arg, EllipsisExpr):
                return default_type

        elif default_factory_args:
            default_factory_type = ctx.arg_types[1][0]

            # Functions that use `ParamSpec` can be overloaded, exposing the callable's types as a parameter.
            # Pydantic calls the default factory without any argument, so we retrieve the first item.
            if isinstance(default_factory_type, Overloaded):
                if MYPY_VERSION_TUPLE > (0, 910):
                    default_factory_type = default_factory_type.items[0]
                else:
                    # Mypy 0.910 exposes the items of overloaded types in a function.
                    default_factory_type = default_factory_type.items()[0]  # type: ignore[operator]

            if isinstance(default_factory_type, CallableType):
                ret_type = default_factory_type.ret_type
                # mypy doesn't think `ret_type` has `args`. This check is added in case it varies by version.
                args = getattr(ret_type, 'args', None)
                if args and all(isinstance(arg, TypeVarType) for arg in args):
                    # If the default factory is a generic type like `list` or `dict`, replace all args with `Any`.
                    ret_type.args = tuple(default_any_type for _ in args)  # type: ignore[attr-defined]

                return ret_type

        return default_any_type
