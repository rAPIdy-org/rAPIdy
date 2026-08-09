# Streaming, downloads, and uploads

Use `HttpClient.stream()` when the response must be consumed incrementally. The
context owns the response body: leaving it closes the transport stream even
after an exception or an early `break`.

```python
async with client.stream(
    "GET", "/reports/{id}", path_params={"id": report_id}
) as response:
    async for chunk in response.aiter_bytes():
        await output.write(chunk)
```

Streaming calls default to `Timeout.total=None`; the configured read timeout
still limits the idle interval between chunks. An explicit `timeout=` overrides
that default. `max_response_size` applies to buffering methods such as
`aread()`, `text()`, and `json()`, but not to `aiter_bytes()`.

`download_to` packages the same context-managed pattern for a local file:

```python
from rapidy_client import download_to

path = await download_to(client, "/reports/latest", "latest.pdf")
```

## Upload bodies

`aiter_file()` is a one-shot, chunked body, so retry is disabled for that
request. Wrap a factory around a source that can be reopened when retries are
safe. Method-preserving redirects such as 307/308 also require replayability;
otherwise the client raises `RedirectBodyNotReplayableError` before attempting
the redirected request.

```python
from pathlib import Path

from rapidy_client import ContentFactory, aiter_file

path = Path("archive.tar.zst")

await client.post("/blobs", content=aiter_file(path))
await client.post("/blobs", content=ContentFactory(lambda: aiter_file(path)))
```

Multipart uploads combine `FilePart` entries and form fields. Path-backed
parts are read in bounded chunks and the multipart body is replayable because
the file is reopened for every attempt.

```python
from rapidy_client import FilePart

await client.post(
    "/documents",
    files=[
        FilePart(name="file", path=Path("report.pdf")),
        FilePart(
            name="metadata",
            content=b'{"quarter": 2}',
            content_type="application/json",
        ),
    ],
    data={"title": "Q2"},
)
```

The declarative API exposes the same form and file capabilities. A `File()`
value is a `FilePart`; the declared parameter name or alias becomes its wire
name.

```python
from typing import Annotated

from rapidy_client import FilePart, Response, bind
from rapidy_client.schema import File, Form, post


@post("/documents")
async def upload_document(
    title: Annotated[str, Form()],
    document: Annotated[FilePart, File()],
) -> Response:
    raise NotImplementedError


upload = bind(upload_document, client)
response = await upload(
    "Q2",
    FilePart(name="document", path=Path("report.pdf")),
)
```

For a lazy declarative download, annotate the endpoint with `Stream` and use
the returned value directly as an async context manager.

```python
from rapidy_client.schema import Stream, get


@get("/reports/latest")
async def latest_report() -> Stream:
    raise NotImplementedError


download = bind(latest_report, client)
async with download() as response:
    async for chunk in response.aiter_bytes():
        await output.write(chunk)
```

`guess_extension(content_type)` is available when a download name must be
derived from a response `Content-Type`; it ignores parameters such as
`charset=utf-8`.
