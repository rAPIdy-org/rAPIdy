from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

from multidict import MultiDict, MultiDictProxy


class MimeType(NamedTuple):
    type: str
    subtype: str
    suffix: str
    parameters: MultiDictProxy[str]


@lru_cache(maxsize=56)
def parse_mimetype(mimetype: str) -> MimeType:
    if not mimetype:
        return MimeType("", "", "", MultiDictProxy(MultiDict()))

    parts = mimetype.split(";")
    parameters: MultiDict[str] = MultiDict()
    for item in parts[1:]:
        if not item:
            continue
        key, _, value = item.partition("=")
        parameters.add(key.lower().strip(), value.strip(' "'))

    full_type = parts[0].strip().lower()
    if full_type == "*":
        full_type = "*/*"
    main_type, _, subtype = full_type.partition("/")
    subtype, _, suffix = subtype.partition("+")
    return MimeType(main_type, subtype, suffix, MultiDictProxy(parameters))


def content_type_matches(actual: str, expected: str) -> bool:
    actual_mime = parse_mimetype(actual)
    expected_mime = parse_mimetype(expected)
    type_matches = expected_mime.type == "*" or expected_mime.type == actual_mime.type
    subtype_matches = (
        expected_mime.subtype == "*" or expected_mime.subtype == actual_mime.subtype
    )
    return type_matches and subtype_matches


__all__ = ("MimeType", "content_type_matches", "parse_mimetype")
