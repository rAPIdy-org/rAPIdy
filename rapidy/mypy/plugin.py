from typing import Callable, cast, Optional, Sequence

from mypy.nodes import EllipsisExpr, Expression
from mypy.plugin import FunctionContext, Plugin
from mypy.types import CallableType, Overloaded, Type, TypeVarType
from pydantic.mypy import MYPY_VERSION_TUPLE

from rapidy.mypy._api_errors import (
    error_default_and_default_factory_specified,
    error_default_or_default_factory_specified,
)
from rapidy.mypy._type_helpers import (
    _name_is_rapidy_param_name,
    _param_can_default,
    CreatedDynamicTypeFunc,
    CreatedTypeFunc,
    return_dynamic_type_map,
    return_static_type_map,
    TypeCreator,
)

# Attribute, to dynamically determine the type of `FormDataBodyRaw` and `MultipartBodyRaw`.
DYNAMIC_TYPE_ATTR_NAME = 'duplicated_attrs_parse_as_array'


class RapidyPlugin(Plugin):
    def get_function_hook(self, fullname: str) -> Optional[Callable[[FunctionContext], Type]]:
        sym = self.lookup_fully_qualified(fullname)
        if sym and _name_is_rapidy_param_name(cast(str, sym.fullname)):
            return self._rapidy_param_callback
        return None

    def _rapidy_param_callback(self, ctx: FunctionContext) -> Type:
        self._raise_assert_error_if_arg_order_is_incorrect(ctx.callee_arg_names)

        default_args = ctx.args[0]
        default_factory_args = ctx.args[1]

        param_name = str(ctx.default_return_type)

        if default_args or default_factory_args:
            if not _param_can_default(param_name):
                error_default_or_default_factory_specified(ctx.api, ctx.context, param_name)
                return TypeCreator.any_explicit()

        if default_args and default_factory_args:
            error_default_and_default_factory_specified(ctx.api, ctx.context)
            return TypeCreator.any_explicit()

        if default_args:
            return self._get_default_arg_type(ctx=ctx, default_args=default_args)

        elif default_factory_args:
            return self._get_default_factory_arg_return_type(ctx=ctx)

        return self._get_param_type_by_function_ctx(ctx)

    def _raise_assert_error_if_arg_order_is_incorrect(self, callee_arg_names: Sequence[Optional[str]]) -> None:
        # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
        assert callee_arg_names[0] == 'default', '`default` is no longer first argument in ParamFieldInfo()'
        assert callee_arg_names[1] == 'default_factory', (
            '`default_factory` is no longer second argument in ParamFieldInfo()'
        )

    def _get_default_arg_type(self, ctx: FunctionContext, default_args: Sequence[Expression]) -> Type:
        # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
        default_type = ctx.arg_types[0][0]
        default_arg = default_args[0]

        # Fallback to default Any type if the Param is required
        if not isinstance(default_arg, EllipsisExpr):
            return default_type

        return TypeCreator.any_explicit()

    def _get_default_factory_arg_return_type(self, ctx: FunctionContext) -> Type:
        # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
        default_factory_type = ctx.arg_types[1][0]

        # Functions which use `ParamSpec` can be overloaded, exposing the callable's types as a parameter
        # Pydantic calls the default factory without any argument, so we retrieve the first item
        if isinstance(default_factory_type, Overloaded):
            if MYPY_VERSION_TUPLE > (0, 910):
                default_factory_type = default_factory_type.items[0]
            else:
                # Mypy0.910 exposes the items of overloaded types in a function
                default_factory_type = default_factory_type.items()[0]  # type: ignore[operator]

        if isinstance(default_factory_type, CallableType):
            ret_type = default_factory_type.ret_type
            # mypy doesn't think `ret_type` has `args`, you'd think mypy should know,
            # add this check in case it varies by version
            args = getattr(ret_type, 'args', None)
            if args:
                if all(isinstance(arg, TypeVarType) for arg in args):
                    # Looks like the default factory is a type like `list` or `dict`, replace all args with `Any`
                    ret_type.args = tuple(TypeCreator.any_explicit() for _ in args)  # type: ignore[attr-defined]
            return ret_type

        return TypeCreator.any_explicit()

    def _get_param_type_by_function_ctx(self, ctx: FunctionContext) -> Type:
        type_created_func: CreatedTypeFunc = return_static_type_map.get(ctx[4].type.name)  # type: ignore
        if type_created_func is not None:
            return type_created_func(ctx.api)  # type: ignore[arg-type]

        dynamic_type_created_func: CreatedDynamicTypeFunc = return_dynamic_type_map.get(ctx[4].type.name)
        if dynamic_type_created_func is not None:

            arg_value_is_true = False
            dynamic_attr = ctx.arg_names[4]

            if dynamic_attr:
                arg_name_is_duplicated_attrs_parse_as_array = dynamic_attr[0] == DYNAMIC_TYPE_ATTR_NAME

                if arg_name_is_duplicated_attrs_parse_as_array:
                    arg_value_is_true = ctx.arg_types[4][0].last_known_value.value is True  # noqa: WPS219

            return dynamic_type_created_func(ctx.api, arg_value_is_true)

        return TypeCreator.any_explicit()
