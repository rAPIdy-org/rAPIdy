from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rapidy_client import (
    UNSET,
    URL,
    Headers,
    RedirectConfig,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
    errors,
)
from rapidy_client._redaction import DENY_HEADERS, DENY_QUERY
from rapidy_client.config import LogConfig
from rapidy_client.observability import LoggingObserver, RequestContext

_SECRETS = st.from_regex(r"S_[A-Z0-9]{8,20}", fullmatch=True)


def _request(
    secret: str,
    *,
    header: str = "Authorization",
    query: str = "token",
) -> Request:
    return Request(
        method="POST",
        url=URL(f"https://example.test/x?{query}={secret}"),
        headers=Headers({header: secret}),
        content=f'{{"token": "{secret}"}}'.encode(),
        extensions=RequestExtensions(
            upstream="catalog",
            endpoint="/x",
            request_id="request-1",
            timeout=Timeout(),
            retry=None,
            idempotent=False,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )


def _response(secret: str) -> Response:
    response = Response(
        status=503,
        headers=Headers({"Set-Cookie": f"session={secret}"}),
        request=_request(secret),
        extensions=ResponseExtensions(elapsed=0.1, attempt=1),
    )
    response._buffered = f'{{"api_key": "{secret}"}}'.encode()
    response._consumed = True
    return response


def _subclasses(
    root: type[errors.HttpClientError],
) -> Iterator[type[errors.HttpClientError]]:
    for child in root.__subclasses__():
        yield child
        yield from _subclasses(child)


def _error_instances(secret: str) -> list[errors.HttpClientError]:
    response = _response(secret)
    result: list[errors.HttpClientError] = []
    for error_type in (errors.HttpClientError, *_subclasses(errors.HttpClientError)):
        message = f"Authorization: Bearer {secret}"
        context = {
            "upstream": "catalog",
            "endpoint": "/x",
            "request_id": "request-1",
        }
        if error_type is errors.HttpTimeoutError:
            error = error_type(message, phase="read", **context)
        elif error_type is errors.StatusError:
            error = error_type(message, status=503, response=response, **context)
        elif error_type is errors.WSHandshakeError:
            error = error_type(message, status=503, **context)
        elif error_type is errors.WSClosedError:
            error = error_type(message, code=1006, reason="closed", **context)
        elif error_type is errors.CircuitOpenError:
            error = error_type(message, retry_after_hint=1.0, **context)
        else:
            error = error_type(message, **context)
        result.append(error)
    return result


@settings(max_examples=40, deadline=None)
@given(
    secret=_SECRETS,
    name=st.sampled_from(sorted(DENY_HEADERS | DENY_QUERY)),
)
def test_error_tree_str_and_repr_never_leak_denylisted_value(
    secret: str,
    name: str,
) -> None:
    for error in _error_instances(secret):
        error.args = (f"{name}: {secret}",)
        assert secret not in str(error)
        assert secret not in repr(error)


@settings(max_examples=40, deadline=None)
@given(
    secret=_SECRETS,
    header=st.sampled_from(sorted(DENY_HEADERS)),
    query=st.sampled_from(sorted(DENY_QUERY)),
)
def test_model_repr_never_leaks_headers_or_query(
    secret: str,
    header: str,
    query: str,
) -> None:
    request = _request(secret, header=header, query=query)
    response = _response(secret)
    assert secret not in repr(request.url)
    assert secret not in str(request.url)
    assert secret not in repr(request.headers)
    assert secret not in repr(request)
    assert secret not in repr(response)


@settings(max_examples=40, deadline=None)
@given(secret=_SECRETS)
def test_status_error_repr_redacts_body_and_url(secret: str) -> None:
    response = _response(secret)
    error = errors.StatusError(
        f"Cookie: session={secret}",
        status=503,
        response=response,
    )
    assert secret not in repr(error)
    assert secret not in str(error)


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.mark.asyncio
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    secret=_SECRETS,
    header=st.sampled_from(sorted(DENY_HEADERS)),
    query=st.sampled_from(sorted(DENY_QUERY)),
)
async def test_logging_observer_never_leaks_denylisted_values(
    secret: str,
    header: str,
    query: str,
) -> None:
    request = _request(secret, header=header, query=query)
    response = _response(secret)
    response.request = request
    handler = _CaptureHandler()
    logger = logging.getLogger(f"property.http.{secret}")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    observer = LoggingObserver(LogConfig(level="body"), logger=logger)
    ctx = RequestContext(
        upstream="catalog",
        method="POST",
        endpoint="/x",
        url=request.url,
        attempt=1,
        request_id="request-1",
        started_at=1.0,
        elapsed=0.1,
    )
    await observer.on_request_end(ctx, response)
    assert len(handler.messages) == 1
    assert secret not in handler.messages[0]
