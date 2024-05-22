from typing import Any, get_args, get_origin, Tuple, Union


def annotation_is_optional(annotation: Any) -> bool:
    if get_origin(annotation) is not Union:
        return False

    return type(None) in get_args(annotation)


def get_base_annotations(annotation: Any) -> Tuple[Any, ...]:
    annotation_origin = get_origin(annotation)
    if annotation_origin is Union:
        annotated_args = get_args(annotation)
        if len(annotated_args) == 1:
            if annotated_args[0] is not None:
                return annotated_args
            return ()

        return tuple(filter(lambda x: x != type(None), annotated_args))

    return (annotation,)
