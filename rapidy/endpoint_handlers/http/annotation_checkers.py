from typing import Any

from rapidy import StreamReader
from rapidy.annotation_checkers import get_base_annotations, lenient_issubclass
from rapidy.web_request import Request
from rapidy.web_response import StreamResponse


def annotation_is_request(annotation: Any) -> bool:
    return lenient_issubclass(annotation, Request)


def annotation_is_stream_response(annotation: Any) -> bool:
    return lenient_issubclass(annotation, StreamResponse)


def is_stream_reader(annotation: Any, *, can_optional: bool = False) -> bool:
    if can_optional:
        return any(base_annotation == StreamReader for base_annotation in get_base_annotations(annotation))
    return annotation is StreamReader
