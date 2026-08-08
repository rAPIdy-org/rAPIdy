import dataclasses
import inspect
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

import pytest
import rapidy_client
import rapidy_core
import yarl
from rapidy_client import (
    UNSET,
    URL,
    AttemptListener,
    AttemptOutcome,
    AuthPolicy,
    BaseTransport,
    BodyTooLargeError,
    ContentFactory,
    DecodeError,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Result,
    Timeout,
)


def _request(
    *,
    content: bytes | AsyncIterable[bytes] | ContentFactory | None = None,
    url: str = "https://h/p",
    headers: Headers | None = None,
) -> Request:
    extensions = RequestExtensions(
        upstream="test",
        endpoint="/p",
        request_id="request-1",
        timeout=Timeout(),
        retry=None,
        idempotent=True,
        auth_override=UNSET,
        deadline=None,
        redirects=None,  # type: ignore[arg-type]
    )
    return Request(
        method="GET",
        url=URL(url),
        headers=headers or Headers(),
        content=content,
        extensions=extensions,
    )


def _response(
    *,
    status: int = 200,
    headers: Headers | None = None,
    stream: AsyncIterable[bytes] | None = None,
    on_close: Any = None,
    max_response_size: int | None = None,
) -> Response:
    return Response(
        status=status,
        headers=headers or Headers(),
        request=_request(),
        extensions=ResponseExtensions(elapsed=0.1, attempt=1),
        stream=stream,
        on_close=on_close,
        max_response_size=max_response_size,
    )


async def _stream(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


def test_timeout_defaults() -> None:
    timeout = Timeout()
    assert (
        timeout.total,
        timeout.connect,
        timeout.read,
        timeout.write,
        timeout.pool,
    ) == (10.0, 3.0, 10.0, 30.0, 5.0)


def test_timeout_kw_only() -> None:
    with pytest.raises(TypeError):
        Timeout(1.0)  # type: ignore[misc]
    assert Timeout(total=None).total is None


def test_url_raw_components() -> None:
    url = URL("https://h:8443/p?token=x&a=1")
    assert (url.scheme, url.host, url.port, url.path, url.query_string) == (
        "https",
        "h",
        8443,
        "/p",
        "token=x&a=1",
    )


def test_url_repr_and_str_redact_query() -> None:
    url = URL("https://h/p?token=SECRET")
    assert "SECRET" not in str(url)
    assert "SECRET" not in repr(url)


def test_url_raw_str_unredacted() -> None:
    assert "SECRET" in URL("https://h/p?token=SECRET")._raw_str()


def test_url_immutable_join_with_query() -> None:
    url = URL("https://h/base?x=1")
    joined = url.join("/next")
    queried = url.with_query({"a": "2"})
    assert isinstance(joined, URL)
    assert isinstance(queried, URL)
    assert joined is not url
    assert queried is not url
    assert url.query_string == "x=1"
    assert joined.path == "/next"
    assert queried.query_string == "a=2"


def test_url_origin() -> None:
    assert URL("https://h:8443/p?x=1").origin() == "https://h:8443"


def test_url_no_yarl_leak() -> None:
    url = URL("https://h/p")
    assert type(url.scheme) is str
    assert not isinstance(url.join("/a"), yarl.URL)
    assert type(url.origin()) is str


def test_headers_case_insensitive() -> None:
    headers = Headers([("Content-Type", "text/plain")])
    assert headers.get("content-type") == "text/plain"
    assert headers.get("Missing", "d") == "d"
    assert headers["CONTENT-TYPE"] == "text/plain"
    assert "content-type" in headers


def test_headers_multivalue_set_cookie() -> None:
    items = [("Set-Cookie", "a=1"), ("Set-Cookie", "b=2")]
    headers = Headers(items)
    assert headers.get_all("set-cookie") == ["a=1", "b=2"]
    assert headers.multi_items() == items
    assert list(headers) == ["Set-Cookie"]
    assert len(headers) == 1


def test_headers_repr_redacts() -> None:
    assert "Bearer S" not in repr(Headers([("Authorization", "Bearer S")]))


def test_result_carries_value_status_headers() -> None:
    model = {"id": 1}
    headers = Headers({"X-Test": "yes"})
    result = Result(value=model, status=201, headers=headers)
    assert (result.value, result.status, result.headers) == (model, 201, headers)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = 200  # type: ignore[misc]


def test_request_is_replayable_bytes() -> None:
    assert _request(content=b"x").is_replayable is True


def test_request_is_replayable_none() -> None:
    assert _request(content=None).is_replayable is True


def test_request_is_replayable_contentfactory() -> None:
    assert _request(content=ContentFactory(lambda: b"x")).is_replayable is True


def test_request_is_replayable_async_gen_false() -> None:
    assert _request(content=_stream(b"x")).is_replayable is False


def test_request_repr_redacts() -> None:
    request = _request(
        url="https://h/p?token=SECRET",
        headers=Headers({"Authorization": "Bearer SECRET"}),
    )
    assert "SECRET" not in repr(request)


@pytest.mark.parametrize(
    ("status", "predicate"),
    [
        (200, "is_success"),
        (299, "is_success"),
        (301, "is_redirect"),
        (404, "is_client_error"),
        (503, "is_server_error"),
    ],
)
def test_response_status_predicates(status: int, predicate: str) -> None:
    assert getattr(_response(status=status), predicate) is True


@pytest.mark.asyncio
async def test_response_aread_buffers_and_caches() -> None:
    consumed = 0

    async def source() -> AsyncIterator[bytes]:
        nonlocal consumed
        for chunk in (b"one", b"two", b"three"):
            consumed += 1
            yield chunk

    response = _response(stream=source())
    first = await response.aread()
    second = await response.aread()
    assert first is second
    assert first == b"onetwothree"
    assert consumed == 3


@pytest.mark.asyncio
async def test_response_aread_over_limit_raises() -> None:
    response = _response(stream=_stream(b"0123456789"), max_response_size=4)
    with pytest.raises(BodyTooLargeError):
        await response.aread()


@pytest.mark.asyncio
async def test_response_text_charset() -> None:
    utf16 = _response(
        headers=Headers({"Content-Type": "text/plain; charset=utf-16"}),
        stream=_stream("привет".encode("utf-16")),
    )
    utf8 = _response(stream=_stream(b"hello"))
    assert await utf16.text() == "привет"
    assert await utf8.text() == "hello"


@pytest.mark.asyncio
async def test_response_json_ok_and_bad() -> None:
    assert await _response(stream=_stream(b'{"ok": true}')).json() == {"ok": True}
    with pytest.raises(DecodeError):
        await _response(stream=_stream(b"not-json")).json()


@pytest.mark.asyncio
async def test_response_aiter_bytes_default_chunk() -> None:
    assert (
        inspect.signature(Response.aiter_bytes).parameters["chunk_size"].default
        == 65536
    )
    response = _response(stream=_stream(b"abcdef"))
    assert [chunk async for chunk in response.aiter_bytes(2)] == [
        b"ab",
        b"cd",
        b"ef",
    ]


@pytest.mark.asyncio
async def test_response_aiter_lines() -> None:
    response = _response(stream=_stream(b"a\n", b"b\n"))
    assert [line async for line in response.aiter_lines()] == ["a", "b"]


@pytest.mark.asyncio
async def test_response_aclose_idempotent() -> None:
    class Stream:
        closed = 0

        def __aiter__(self) -> AsyncIterator[bytes]:
            return _stream(b"x")

        async def aclose(self) -> None:
            self.closed += 1

    stream = Stream()
    response = _response(stream=stream)
    await response.aclose()
    await response.aclose()
    assert stream.closed == 1


@pytest.mark.asyncio
async def test_response_aclose_calls_on_close() -> None:
    closed = 0

    async def on_close() -> None:
        nonlocal closed
        closed += 1

    response = _response(stream=_stream(b"unread"), on_close=on_close)
    await response.aclose()
    await response.aclose()
    assert closed == 1


@pytest.mark.asyncio
async def test_response_single_consumer() -> None:
    response = _response(stream=_stream(b"body"))
    assert [chunk async for chunk in response.aiter_bytes()] == [b"body"]
    with pytest.raises(RuntimeError):
        await response.aread()


def test_request_extensions_registry_fields() -> None:
    assert {item.name for item in dataclasses.fields(RequestExtensions)} == {
        "upstream",
        "endpoint",
        "request_id",
        "timeout",
        "retry",
        "idempotent",
        "auth_override",
        "deadline",
        "redirects",
        "declared_middlewares",
        "attempt",
        "attempt_listeners",
        "custom",
    }
    extensions = _request().extensions
    assert extensions.declared_middlewares == ()
    assert extensions.attempt == 0
    assert extensions.attempt_listeners == []
    assert extensions.custom == {}


def test_response_extensions_fields() -> None:
    assert {item.name for item in dataclasses.fields(ResponseExtensions)} == {
        "elapsed",
        "attempt",
        "connection_reused",
        "pool_wait",
    }
    extensions = ResponseExtensions(elapsed=0.1, attempt=1)
    assert extensions.connection_reused is None
    assert extensions.pool_wait is None


def test_protocols_structural() -> None:
    class Transport:
        async def handle(self, request: Request) -> Response:
            return _response()

        async def aclose(self) -> None:
            pass

    class Listener:
        def on_attempt(self, outcome: AttemptOutcome) -> None:
            pass

    assert isinstance(Transport(), BaseTransport)
    assert isinstance(Listener(), AttemptListener)
    assert AttemptOutcome.__required_keys__ == {"status", "exception", "elapsed"}


def test_auth_policy_is_protocol() -> None:
    assert issubclass(AuthPolicy, object)
    assert getattr(AuthPolicy, "_is_protocol", False) is True


def test_facade_reexports_unset() -> None:
    assert rapidy_client.UNSET is rapidy_core.UNSET
    assert rapidy_client.Unset is rapidy_core.Unset


def test_facade_no_markers() -> None:
    assert not hasattr(rapidy_client, "PathParam")
    assert not hasattr(rapidy_client, "QueryParam")


def test_facade_all_importable() -> None:
    assert all(hasattr(rapidy_client, name) for name in rapidy_client.__all__)
