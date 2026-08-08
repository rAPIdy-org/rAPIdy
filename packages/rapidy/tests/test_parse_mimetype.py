from __future__ import annotations

import pytest
from multidict import MultiDictProxy

from rapidy.helpers import MimeType, parse_mimetype


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('application/json', ('application', 'json', '', {})),
        ('application/vnd.api+json; charset=utf-8', ('application', 'vnd.api', 'json', {'charset': 'utf-8'})),
        ('text/html; charset=utf-8', ('text', 'html', '', {'charset': 'utf-8'})),
        ('text/*', ('text', '*', '', {})),
        ('*/*', ('*', '*', '', {})),
        ('*', ('*', '*', '', {})),
        ('', ('', '', '', {})),
        ('Application/JSON', ('application', 'json', '', {})),
        (' text/html ', ('text', 'html', '', {})),
        ('text/html; charset="utf-8"', ('text', 'html', '', {'charset': 'utf-8'})),
        ('text/html; foo', ('text', 'html', '', {'foo': ''})),
        ('text/html;; charset=utf-8', ('text', 'html', '', {'charset': 'utf-8'})),
    ],
)
def test_parse_mimetype_reference_cases(
    raw: str,
    expected: tuple[str, str, str, dict[str, str]],
) -> None:
    parsed = parse_mimetype(raw)
    assert (parsed.type, parsed.subtype, parsed.suffix) == expected[:3]
    assert dict(parsed.parameters) == expected[3]


def test_mimetype_public_shape_and_cache() -> None:
    first = parse_mimetype('application/json')
    second = parse_mimetype('application/json')

    assert MimeType._fields == ('type', 'subtype', 'suffix', 'parameters')
    assert isinstance(first.parameters, MultiDictProxy)
    assert first is second
    assert parse_mimetype.__wrapped__
