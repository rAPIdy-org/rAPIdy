from __future__ import annotations

import json

import pytest

from spikes._mini.testing import CountingReceive, make_scope
from spikes.spike_b_extraction.extraction_proto import (
    FileField,
    IncorrectContentTypeError,
    RequestEntityTooLarge,
    RequestProto,
    ensure_content_type,
    extract_all_sources,
)


@pytest.mark.asyncio
async def test_read_once() -> None:
    receive = CountingReceive(
        [{"type": "http.request", "body": b"hello", "more_body": False}]
    )
    request = RequestProto(make_scope(method="POST"), receive)
    assert await request.read() == b"hello"
    assert await request.read() == b"hello"
    assert receive.calls == 1


@pytest.mark.asyncio
async def test_client_max_size_413() -> None:
    receive = CountingReceive(
        [{"type": "http.request", "body": b"12345", "more_body": False}]
    )
    request = RequestProto(make_scope(method="POST"), receive, client_max_size=4)
    with pytest.raises(RequestEntityTooLarge):
        await request.read()


@pytest.mark.asyncio
async def test_urlencoded_form_and_limit() -> None:
    body = b"name=first&name=second&empty="
    scope = make_scope(
        method="POST",
        headers=[
            (b"content-type", b"application/x-www-form-urlencoded; charset=utf-8")
        ],
    )
    request = RequestProto(
        scope, CountingReceive([{"type": "http.request", "body": body}])
    )
    form = await request.post()
    assert form.getall("name") == ["first", "second"]
    assert form["empty"] == ""

    limited = RequestProto(
        scope,
        CountingReceive([{"type": "http.request", "body": body}]),
        client_max_size=5,
    )
    with pytest.raises(RequestEntityTooLarge):
        await limited.post()


@pytest.mark.asyncio
async def test_all_sources_one_request() -> None:
    body = json.dumps({"name": "demo"}).encode()
    scope = make_scope(
        method="POST",
        path="/items/42",
        query_string=b"q=search",
        headers=[
            (b"content-type", b"application/json"),
            (b"x-token", b"secret"),
            (b"cookie", b"session=abc"),
        ],
    )
    scope["path_params"] = {"item_id": "42"}
    request = RequestProto(
        scope, CountingReceive([{"type": "http.request", "body": body}])
    )
    assert await extract_all_sources(request) == {
        "body": {"name": "demo"},
        "header": "secret",
        "cookie": "abc",
        "path": "42",
        "query": "search",
    }


def test_filefield_structure() -> None:
    assert FileField._fields == ("name", "filename", "file", "content_type", "headers")


def test_content_type_errors_match_legacy_text() -> None:
    with pytest.raises(IncorrectContentTypeError) as empty:
        ensure_content_type("", "application/*")
    assert (
        empty.value.error
        == "`Content-Type` header cannot be empty. Expected: `application/*`"
    )

    with pytest.raises(IncorrectContentTypeError) as mismatch:
        ensure_content_type("text/plain", "application/json")
    assert (
        mismatch.value.error
        == "Expected Content-Type `application/json` not `text/plain`"
    )
