from __future__ import annotations

import inspect
from functools import partial
from typing import Any, Callable, Tuple, Union
from typing_extensions import Annotated, get_args, get_origin

from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import Unset, UnsetType
from rapidy.version import PY_VERSION_TUPLE

if PYDANTIC_IS_V1:
    from pydantic.utils import lenient_issubclass
else:
    from pydantic._internal._utils import lenient_issubclass

__all__ = (
    'lenient_issubclass',
    'is_union',
    'is_optional',
    'is_annotated',
    'is_empty',
)


if PY_VERSION_TUPLE >= (3, 10, 0):
    from types import UnionType  # type: ignore[attr-defined, unused-ignore]

    def is_union(annotation: Any) -> bool:
        """Check if the annotation is a Union type.

        Args:
            annotation (Any): The annotation to check.

        Returns:
            bool: True if the annotation is a Union or UnionType, False otherwise.
        """
        origin = get_origin(annotation)
        return origin is UnionType or origin is Union

else:

    def is_union(annotation: Any) -> bool:
        """Check if the annotation is a Union type.

        Args:
            annotation (Any): The annotation to check.

        Returns:
            bool: True if the annotation is a Union, False otherwise.
        """
        return get_origin(annotation) is Union


def is_optional(annotation: Any) -> bool:
    """Check if the annotation is an Optional type.

    Optional is considered as a Union with `None`.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: True if the annotation is Optional (i.e., Union with None), False otherwise.
    """
    if is_union(annotation):
        return type(None) in get_args(annotation)

    return False


def is_annotated(annotation: Any) -> bool:
    """Check if the annotation is an Annotated type.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: True if the annotation is an Annotated type, False otherwise.
    """
    return get_origin(annotation) is Annotated


def get_base_annotations(annotation: Any) -> Tuple[Any, ...]:
    """Get the base annotations from a given annotation.

    This function handles `Union` and `Annotated` types, extracting the relevant base types
    and filtering out `None` from `Union` annotations if present.

    Args:
        annotation (Any): The annotation to extract base annotations from.

    Returns:
        Tuple[Any, ...]: A tuple of base annotations.
    """
    if is_union(annotation):
        annotated_args = get_args(annotation)
        if len(annotated_args) == 1:
            if annotated_args[0] is not None:
                return annotated_args
            return ()

        return tuple(filter(lambda x: x != type(None), annotated_args))  # noqa: E721

    if is_annotated(annotation):
        return (get_args(annotation)[0],)

    return (annotation,)


def is_empty(obj: Any) -> bool:
    """Check if the object is empty, i.e., if it is `inspect.Signature.empty`.

    Args:
        obj (Any): The object to check.

    Returns:
        bool: True if the object is `inspect.Signature.empty`, False otherwise.
    """
    return obj is inspect.Signature.empty


def is_not_none_and_unset(field_value: Any | UnsetType) -> bool:
    """Check if the field value is neither `None` nor `Unset`.

    Args:
        field_value (Union[Any, UnsetType]): The field value to check.

    Returns:
        bool: True if the field value is neither `None` nor `Unset`, False otherwise.
    """
    return field_value is not None and field_value is not Unset


def is_async_callable(func: Callable[..., Any]) -> Any:
    """Check if a function is an asynchronous callable.

    This function checks whether the given function or its base function (in case of partial)
    is an asynchronous function.

    Args:
        func (Callable[..., Any]): The function to check.

    Returns:
        bool: True if the function is asynchronous, False otherwise.
    """
    base_function = func.func if isinstance(func, partial) else func

    return inspect.iscoroutinefunction(func) or (
        callable(base_function) and inspect.iscoroutinefunction(base_function.__call__)  # type: ignore[operator]
    )
