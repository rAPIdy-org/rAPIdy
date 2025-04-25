from __future__ import annotations

from typing import Any

from rapidy import StreamReader
from rapidy.annotation_checkers import get_base_annotations, lenient_issubclass
from rapidy.web_request import Request
from rapidy.web_response import StreamResponse


def annotation_is_request(annotation: Any) -> bool:
    """Checks if the given annotation is a subclass of `Request`.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: True if the annotation is a subclass of `Request`, otherwise False.
    """
    return lenient_issubclass(annotation, Request)


def annotation_is_stream_response(annotation: Any) -> bool:
    """Checks if the given annotation is a subclass of `StreamResponse`.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: True if the annotation is a subclass of `StreamResponse`, otherwise False.
    """
    return lenient_issubclass(annotation, StreamResponse)


def is_stream_reader(annotation: Any, *, can_optional: bool = False) -> bool:
    """Checks if the given annotation is `StreamReader` or its subclass.

    Args:
        annotation (Any): The annotation to check.
        can_optional (bool, optional): If True, allows checking for `Optional[StreamReader]`. Defaults to False.

    Returns:
        bool: True if the annotation is `StreamReader` or a subclass
              (or `Optional[StreamReader]` if `can_optional` is True), otherwise False.
    """
    if can_optional:
        return any(base_annotation == StreamReader for base_annotation in get_base_annotations(annotation))
    return annotation is StreamReader
