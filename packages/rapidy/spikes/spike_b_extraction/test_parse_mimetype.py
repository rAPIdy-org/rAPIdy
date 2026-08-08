from __future__ import annotations

import pytest
from aiohttp.helpers import parse_mimetype as aiohttp_parse_mimetype

from spikes.spike_b_extraction.mimetype_proto import (
    content_type_matches,
    parse_mimetype,
)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "*",
        "application/json",
        "application/vnd.api+json; charset=utf-8",
        "text/plain; charset=windows-1251",
        "multipart/form-data; boundary=demo",
        "application/json; profile=one; profile=two",
        " IMAGE/PNG ",
        'application/problem+json; charset="utf-8"',
    ],
)
def test_parse_mimetype_matches_aiohttp(value: str) -> None:
    actual = parse_mimetype(value)
    expected = aiohttp_parse_mimetype(value)
    assert (actual.type, actual.subtype, actual.suffix) == (
        expected.type,
        expected.subtype,
        expected.suffix,
    )
    assert list(actual.parameters.items()) == list(expected.parameters.items())


def test_content_type_wildcards() -> None:
    assert content_type_matches("application/json", "application/*")
    assert content_type_matches("text/plain", "*/*")
    assert not content_type_matches("text/plain", "application/*")
