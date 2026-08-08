from __future__ import annotations

import inspect
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from rapidy_core.typedefs import UNSET

__all__ = (
    "get_base_annotations",
    "is_annotated",
    "is_empty",
    "is_not_none_and_unset",
    "is_optional",
    "is_union",
    "lenient_issubclass",
)


def lenient_issubclass(
    cls: Any, class_or_tuple: type[Any] | tuple[type[Any], ...]
) -> bool:
    """Return whether ``cls`` is a subclass without failing for non-class inputs."""
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)
    except TypeError:
        return False


def is_union(annotation: Any) -> bool:
    """Return whether an annotation is either spelling of a union."""
    origin = get_origin(annotation)
    return origin is UnionType or origin is Union


def is_optional(annotation: Any) -> bool:
    """Return whether an annotation is a union containing ``None``."""
    if is_union(annotation):
        return type(None) in get_args(annotation)
    return False


def is_annotated(annotation: Any) -> bool:
    """Return whether an annotation uses ``typing.Annotated``."""
    return get_origin(annotation) is Annotated


def get_base_annotations(annotation: Any) -> tuple[Any, ...]:
    """Unwrap union or annotated metadata into its base annotations."""
    if is_union(annotation):
        annotated_args = get_args(annotation)
        if len(annotated_args) == 1:
            if annotated_args[0] is not None:
                return annotated_args
            return ()
        return tuple(item for item in annotated_args if item is not type(None))

    if is_annotated(annotation):
        return (get_args(annotation)[0],)

    return (annotation,)


def is_empty(obj: Any) -> bool:
    """Return whether an object is ``inspect.Signature.empty``."""
    return obj is inspect.Signature.empty


def is_not_none_and_unset(field_value: Any) -> bool:
    """Return whether a value is neither ``None`` nor the unset sentinel."""
    return field_value is not None and field_value is not UNSET
