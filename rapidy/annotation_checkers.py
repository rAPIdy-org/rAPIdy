import inspect
from functools import partial
from typing import Any, Callable, Tuple, Union

from typing_extensions import Annotated, get_args, get_origin

from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import Unset
from rapidy.version import PY_VERSION_TUPLE

if PYDANTIC_IS_V1:
    from pydantic.utils import lenient_issubclass as lenient_issubclass  # noqa: F401 WPS433 WPS440
else:
    from pydantic._internal._utils import lenient_issubclass as lenient_issubclass  # noqa: F401 WPS433 WPS440

__all__ = (
    'lenient_issubclass',
    'is_union',
    'is_optional',
    'is_annotated',
    'is_empty',
)


if PY_VERSION_TUPLE >= (3, 10, 0):
    from types import UnionType  # type: ignore[attr-defined, unused-ignore]  # noqa: WPS433

    def is_union(annotation: Any) -> bool:
        origin = get_origin(annotation)
        return origin is UnionType or origin is Union

else:
    def is_union(annotation: Any) -> bool:  # noqa: WPS440
        return get_origin(annotation) is Union


def is_optional(annotation: Any) -> bool:
    if is_union(annotation):
        return type(None) in get_args(annotation)  # noqa: WPS516

    return False


def is_annotated(annotation: Any) -> bool:
    return get_origin(annotation) is Annotated


def get_base_annotations(annotation: Any) -> Tuple[Any, ...]:
    if is_union(annotation):
        annotated_args = get_args(annotation)
        if len(annotated_args) == 1:
            if annotated_args[0] is not None:
                return annotated_args
            return ()

        return tuple(filter(lambda x: x != type(None), annotated_args))  # noqa: E721 WPS516

    if is_annotated(annotation):
        return (get_args(annotation)[0],)

    return (annotation,)


def is_empty(obj: Any) -> bool:
    return obj is inspect.Signature.empty


def is_not_none_and_unset(field_value: Any) -> bool:
    return field_value is not None and field_value is not Unset


def is_async_callable(func: Callable[..., Any]) -> Any:
    base_function = func.func if isinstance(func, partial) else func

    return inspect.iscoroutinefunction(func) or (
        callable(base_function)
        and inspect.iscoroutinefunction(base_function.__call__)  # type: ignore[operator]  # noqa: WPS609
    )
