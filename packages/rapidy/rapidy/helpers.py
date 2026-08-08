from __future__ import annotations

import functools
from typing import NamedTuple

from multidict import MultiDict, MultiDictProxy

__all__ = ('MimeType', 'parse_mimetype')


class MimeType(NamedTuple):
    """Parsed MIME type and its parameters."""

    type: str
    subtype: str
    suffix: str
    parameters: MultiDictProxy[str]


@functools.lru_cache(maxsize=56)
def parse_mimetype(mimetype: str) -> MimeType:
    """Parse a MIME value into normalized named components."""
    if not mimetype:
        return MimeType('', '', '', MultiDictProxy(MultiDict()))

    parts = mimetype.split(';')
    params: MultiDict[str] = MultiDict()
    for item in parts[1:]:
        if not item:
            continue
        key, _, value = item.partition('=')
        params.add(key.lower().strip(), value.strip(' "'))

    fulltype = parts[0].strip().lower()
    if fulltype == '*':
        fulltype = '*/*'

    mime_type, _, subtype = fulltype.partition('/')
    subtype, _, suffix = subtype.partition('+')
    return MimeType(mime_type, subtype, suffix, MultiDictProxy(params))
