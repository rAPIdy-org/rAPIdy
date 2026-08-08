import pytest
from rapidy_client import (
    UNSET,
    URL,
    BodyTooLargeError,
    CircuitOpenError,
    ClientClosedError,
    ConnectError,
    DeadlineExceededError,
    DecodeError,
    DNSResolveError,
    Headers,
    HttpClientError,
    HttpTimeoutError,
    MessageValidationError,
    ProtocolError,
    ProxyError,
    RedirectError,
    RedirectNotAllowedError,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    ResponseValidationError,
    SchemaDefinitionError,
    ServerDisconnectedError,
    StatusError,
    Timeout,
    TLSError,
    TooManyRedirectsError,
    TransportError,
    WSClosedError,
    WSError,
    WSHandshakeError,
    WSQueueFullError,
)
from rapidy_client._redaction import CROP_SUFFIX


@pytest.mark.parametrize(
    ("child", "parent"),
    [
        (ClientClosedError, HttpClientError),
        (TransportError, HttpClientError),
        (ConnectError, TransportError),
        (DNSResolveError, ConnectError),
        (TLSError, ConnectError),
        (ProxyError, TransportError),
        (ServerDisconnectedError, TransportError),
        (ProtocolError, TransportError),
        (HttpTimeoutError, TransportError),
        (DeadlineExceededError, HttpClientError),
        (CircuitOpenError, HttpClientError),
        (RedirectError, HttpClientError),
        (TooManyRedirectsError, RedirectError),
        (RedirectNotAllowedError, RedirectError),
        (StatusError, HttpClientError),
        (BodyTooLargeError, HttpClientError),
        (DecodeError, HttpClientError),
        (ResponseValidationError, HttpClientError),
        (WSError, HttpClientError),
        (WSHandshakeError, WSError),
        (WSClosedError, WSError),
        (WSQueueFullError, WSError),
        (MessageValidationError, HttpClientError),
    ],
)
def test_full_tree_hierarchy(
    child: type[BaseException], parent: type[BaseException]
) -> None:
    assert issubclass(child, parent)


def _response(body: bytes = b"") -> Response:
    extensions = RequestExtensions(
        upstream="test",
        endpoint=None,
        request_id=None,
        timeout=Timeout(),
        retry=None,
        idempotent=True,
        auth_override=UNSET,
        deadline=None,
        redirects=None,  # type: ignore[arg-type]
    )
    request = Request(
        method="GET",
        url=URL("https://h/p?token=SECRET"),
        headers=Headers(),
        content=None,
        extensions=extensions,
    )
    response = Response(
        status=503,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.1, attempt=1),
    )
    response._buffered = body
    return response


def test_http_timeout_is_also_timeouterror() -> None:
    assert issubclass(HttpTimeoutError, TimeoutError)
    assert HttpTimeoutError(phase="connect").phase == "connect"


def test_schema_definition_error_outside_tree() -> None:
    assert not issubclass(SchemaDefinitionError, HttpClientError)
    assert issubclass(SchemaDefinitionError, Exception)


def test_each_error_instantiable_with_attrs() -> None:
    simple_errors = [
        HttpClientError,
        ClientClosedError,
        TransportError,
        ConnectError,
        DNSResolveError,
        TLSError,
        ProxyError,
        ServerDisconnectedError,
        ProtocolError,
        DeadlineExceededError,
        RedirectError,
        TooManyRedirectsError,
        RedirectNotAllowedError,
        BodyTooLargeError,
        DecodeError,
        ResponseValidationError,
        WSError,
        WSQueueFullError,
        MessageValidationError,
    ]
    assert all(isinstance(error(), Exception) for error in simple_errors)
    assert CircuitOpenError(retry_after_hint=1.5).retry_after_hint == 1.5
    assert StatusError(status=503, response=_response()).status == 503
    assert WSHandshakeError(status=500).status == 500
    closed = WSClosedError(code=1006, reason="x")
    assert (closed.code, closed.reason) == (1006, "x")


def test_error_carries_context() -> None:
    error = HttpClientError("boom", upstream="billing", endpoint="/x", request_id="r1")
    assert (error.upstream, error.endpoint, error.request_id) == (
        "billing",
        "/x",
        "r1",
    )


def test_error_repr_redacts_secret() -> None:
    error = HttpClientError("Authorization: Bearer TOPSECRET")
    assert "TOPSECRET" not in repr(error)
    assert "TOPSECRET" not in str(error)


def test_status_error_repr_crops_body() -> None:
    body = b"x" * 300
    rendered = repr(StatusError("bad status", status=503, response=_response(body)))
    assert CROP_SUFFIX in rendered
    assert body.decode() not in rendered
    assert "SECRET" not in rendered
