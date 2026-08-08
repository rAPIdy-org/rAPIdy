from __future__ import annotations

import httpx
import pytest

from spikes._mini.serve import live_server
from spikes._mini.testing import CountingReceive, make_scope
from spikes.spike_b_extraction.extraction_proto import (
    FileField,
    RequestEntityTooLarge,
    RequestProto,
)

BOUNDARY = "spike-boundary"
BODY = (
    f"--{BOUNDARY}\r\n"
    'Content-Disposition: form-data; name="title"\r\n\r\n'
    "hello\r\n"
    f"--{BOUNDARY}\r\n"
    'Content-Disposition: form-data; name="upload"; filename="demo.txt"\r\n'
    "Content-Type: text/plain\r\n\r\n"
    "payload\r\n"
    f"--{BOUNDARY}--\r\n"
).encode()


@pytest.mark.asyncio
async def test_multipart_file_and_cache() -> None:
    scope = make_scope(
        method="POST",
        headers=[
            (b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode())
        ],
    )
    request = RequestProto(
        scope, CountingReceive([{"type": "http.request", "body": BODY}])
    )
    form = await request.post()
    assert await request.post() is form
    assert form["title"] == "hello"
    upload = form["upload"]
    assert isinstance(upload, FileField)
    assert upload.filename == "demo.txt"
    assert upload.file.read() == b"payload"


@pytest.mark.asyncio
async def test_multipart_respects_total_size_limit() -> None:
    scope = make_scope(
        method="POST",
        headers=[
            (b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode())
        ],
    )
    request = RequestProto(
        scope,
        CountingReceive([{"type": "http.request", "body": BODY}]),
        client_max_size=len(BODY) - 1,
    )
    with pytest.raises(RequestEntityTooLarge):
        await request.post()


@pytest.mark.parametrize("runtime", ["granian", "uvicorn"])
def test_multipart_e2e(runtime: str) -> None:
    with live_server(runtime, "spikes.spike_b_extraction.app:app") as base_url:
        with httpx.Client(base_url=base_url, timeout=10) as client:
            response = client.post(
                "/multipart",
                data={"title": "hello"},
                files={"upload": ("demo.txt", b"payload", "text/plain")},
            )
    assert response.status_code == 200
    assert response.json() == [
        {"key": "title", "value": "hello"},
        {"key": "upload", "filename": "demo.txt", "size": 7},
    ]
