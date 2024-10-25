from typing import Any, Tuple, Union

from typing_extensions import Annotated, get_args, get_origin

from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.version import PY_VERSION_TUPLE

if PYDANTIC_V1:
    from pydantic.utils import lenient_issubclass as lenient_issubclass  # noqa: F401 WPS433 WPS440
elif PYDANTIC_V2:
    from pydantic._internal._utils import lenient_issubclass as lenient_issubclass  # noqa: F401 WPS433 WPS440
else:
    raise ValueError


if PY_VERSION_TUPLE >= (3, 10, 0):
    from types import UnionType  # type: ignore[attr-defined, unused-ignore]  # noqa: WPS433

    def annotation_is_union(annotation: Any) -> bool:
        origin = get_origin(annotation)
        return origin is UnionType or origin is Union

else:
    def annotation_is_union(annotation: Any) -> bool:  # noqa: WPS440
        return get_origin(annotation) is Union


def annotation_is_optional(annotation: Any) -> bool:
    if annotation_is_union(annotation):
        return type(None) in get_args(annotation)

    return False


def annotation_is_annotated(annotation: Any) -> bool:
    return get_origin(annotation) is Annotated


def get_base_annotations(annotation: Any) -> Tuple[Any, ...]:
    if annotation_is_union(annotation):
        annotated_args = get_args(annotation)
        if len(annotated_args) == 1:
            if annotated_args[0] is not None:
                return annotated_args
            return ()

        return tuple(filter(lambda x: x != type(None), annotated_args))  # noqa: E721

    if annotation_is_annotated(annotation):
        return (get_args(annotation)[0],)

    return (annotation,)
