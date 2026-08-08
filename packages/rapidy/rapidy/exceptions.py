from __future__ import annotations

# ruff: noqa: N818
import http.client
from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast

from multidict import CIMultiDict
from rapidy_core.client_errors import normalize_errors
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.exceptions import RapidyException

from rapidy.typedefs import LooseHeaders, ValidationErrorList

__all__ = [
    'HTTPException',
    'HTTPError',
    'HTTPRedirection',
    'HTTPSuccessful',
    'HTTPOk',
    'HTTPCreated',
    'HTTPAccepted',
    'HTTPNonAuthoritativeInformation',
    'HTTPNoContent',
    'HTTPResetContent',
    'HTTPPartialContent',
    'HTTPMultipleChoices',
    'HTTPMovedPermanently',
    'HTTPFound',
    'HTTPSeeOther',
    'HTTPNotModified',
    'HTTPUseProxy',
    'HTTPTemporaryRedirect',
    'HTTPPermanentRedirect',
    'HTTPClientError',
    'HTTPBadRequest',
    'HTTPUnauthorized',
    'HTTPPaymentRequired',
    'HTTPForbidden',
    'HTTPNotFound',
    'HTTPMethodNotAllowed',
    'HTTPNotAcceptable',
    'HTTPProxyAuthenticationRequired',
    'HTTPRequestTimeout',
    'HTTPConflict',
    'HTTPGone',
    'HTTPLengthRequired',
    'HTTPPreconditionFailed',
    'HTTPRequestEntityTooLarge',
    'HTTPRequestURITooLong',
    'HTTPUnsupportedMediaType',
    'HTTPRequestRangeNotSatisfiable',
    'HTTPExpectationFailed',
    'HTTPMisdirectedRequest',
    'HTTPUnprocessableEntity',
    'HTTPValidationFailure',
    'HTTPFailedDependency',
    'HTTPUpgradeRequired',
    'HTTPPreconditionRequired',
    'HTTPTooManyRequests',
    'HTTPRequestHeaderFieldsTooLarge',
    'HTTPUnavailableForLegalReasons',
    'HTTPServerError',
    'HTTPInternalServerError',
    'HTTPNotImplemented',
    'HTTPBadGateway',
    'HTTPServiceUnavailable',
    'HTTPGatewayTimeout',
    'HTTPVersionNotSupported',
    'HTTPVariantAlsoNegotiates',
    'HTTPInsufficientStorage',
    'HTTPNotExtended',
    'HTTPNetworkAuthenticationRequired',
    'HTTPMove',
]


class ASGIProtocolError(RapidyException):
    """Raised when an ASGI peer sends an unexpected event."""


class RouteConflictError(RapidyException):
    """Raised when a method/path pair is registered twice."""


class ResponseDuplicateBodyError(RapidyException):
    """Raised when both compatibility body inputs are provided."""


class ResponseEncodeError(RapidyException):
    """Reserved for full response serialization in milestone 10."""


def _as_header_text(value: str | bytes) -> str:
    return value.decode('latin-1') if isinstance(value, bytes) else value


def _make_headers(headers: LooseHeaders | None) -> CIMultiDict[str]:
    if headers is None:
        return CIMultiDict()
    if isinstance(headers, Mapping):
        return CIMultiDict(headers)
    return CIMultiDict((_as_header_text(key), _as_header_text(value)) for key, value in headers)


class HTTPException(Exception):
    """Base exception rendered as an HTTP response by the application core."""

    status_code: int = -1
    empty_body: bool = False

    def __init__(
        self,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        if self.status_code == -1:
            msg = f'{type(self).__name__} is an abstract exception and is not intended to be raised'
            raise RuntimeError(msg)
        if reason is None:
            reason = http.client.responses.get(self.status_code, '')
        elif '\r' in reason or '\n' in reason:
            msg = 'Reason cannot contain \\r or \\n'
            raise ValueError(msg)

        self.headers = _make_headers(headers)
        self.reason = reason
        self.body = body
        self.text = text
        self.content_type = content_type
        if body is None and text is None and not self.empty_body:
            self.text = f'{self.status_code}: {self.reason}'
            if content_type is None:
                self.content_type = 'text/plain'
        Exception.__init__(self, self.reason)

    @property
    def status(self) -> int:
        """Return the status-code alias retained from the public 1.x API."""
        return self.status_code


class HTTPSuccessful(HTTPException):
    """Abstract base for successful HTTP control-flow exceptions."""


class HTTPOk(HTTPSuccessful):
    """Represent HTTP 200 OK."""

    status_code = 200


class HTTPCreated(HTTPSuccessful):
    """Represent HTTP 201 Created."""

    status_code = 201


class HTTPAccepted(HTTPSuccessful):
    """Represent HTTP 202 Accepted."""

    status_code = 202


class HTTPNonAuthoritativeInformation(HTTPSuccessful):
    """Represent HTTP 203 Non-Authoritative Information."""

    status_code = 203


class HTTPNoContent(HTTPSuccessful):
    """Represent HTTP 204 No Content."""

    status_code = 204
    empty_body = True


class HTTPResetContent(HTTPSuccessful):
    """Represent HTTP 205 Reset Content."""

    status_code = 205
    empty_body = True


class HTTPPartialContent(HTTPSuccessful):
    """Represent HTTP 206 Partial Content."""

    status_code = 206


class HTTPRedirection(HTTPException):
    """Abstract base for HTTP redirection exceptions."""


class HTTPMove(HTTPRedirection):
    """Abstract base for redirects that require a target location."""

    def __init__(
        self,
        location: str,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        if not location:
            msg = 'HTTP redirects need a location to redirect to.'
            raise ValueError(msg)
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self.headers['Location'] = location
        self.location = location


class HTTPMultipleChoices(HTTPMove):
    """Represent HTTP 300 Multiple Choices."""

    status_code = 300


class HTTPMovedPermanently(HTTPMove):
    """Represent HTTP 301 Moved Permanently."""

    status_code = 301


class HTTPFound(HTTPMove):
    """Represent HTTP 302 Found."""

    status_code = 302


class HTTPSeeOther(HTTPMove):
    """Represent HTTP 303 See Other."""

    status_code = 303


class HTTPNotModified(HTTPRedirection):
    """Represent HTTP 304 Not Modified."""

    status_code = 304
    empty_body = True


class HTTPUseProxy(HTTPMove):
    """Represent HTTP 305 Use Proxy."""

    status_code = 305


class HTTPTemporaryRedirect(HTTPMove):
    """Represent HTTP 307 Temporary Redirect."""

    status_code = 307


class HTTPPermanentRedirect(HTTPMove):
    """Represent HTTP 308 Permanent Redirect."""

    status_code = 308


class HTTPError(HTTPException):
    """Abstract base for HTTP error exceptions."""


class HTTPClientError(HTTPError):
    """Abstract base for HTTP 4xx exceptions."""


class HTTPBadRequest(HTTPClientError):
    """Represent HTTP 400 Bad Request."""

    status_code = 400


class HTTPUnauthorized(HTTPClientError):
    """Represent HTTP 401 Unauthorized."""

    status_code = 401


class HTTPPaymentRequired(HTTPClientError):
    """Represent HTTP 402 Payment Required."""

    status_code = 402


class HTTPForbidden(HTTPClientError):
    """Represent HTTP 403 Forbidden."""

    status_code = 403


class HTTPNotFound(HTTPClientError):
    """Represent HTTP 404 Not Found."""

    status_code = 404


class HTTPMethodNotAllowed(HTTPClientError):
    """Represent HTTP 405 Method Not Allowed with its Allow metadata."""

    status_code = 405

    def __init__(
        self,
        method: str,
        allowed_methods: Iterable[str],
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.method = method.upper()
        self.allowed_methods = set(allowed_methods)
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self.headers['Allow'] = ', '.join(sorted(self.allowed_methods))


class HTTPNotAcceptable(HTTPClientError):
    """Represent HTTP 406 Not Acceptable."""

    status_code = 406


class HTTPProxyAuthenticationRequired(HTTPClientError):
    """Represent HTTP 407 Proxy Authentication Required."""

    status_code = 407


class HTTPRequestTimeout(HTTPClientError):
    """Represent HTTP 408 Request Timeout."""

    status_code = 408


class HTTPConflict(HTTPClientError):
    """Represent HTTP 409 Conflict."""

    status_code = 409


class HTTPGone(HTTPClientError):
    """Represent HTTP 410 Gone."""

    status_code = 410


class HTTPLengthRequired(HTTPClientError):
    """Represent HTTP 411 Length Required."""

    status_code = 411


class HTTPPreconditionFailed(HTTPClientError):
    """Represent HTTP 412 Precondition Failed."""

    status_code = 412


class HTTPRequestEntityTooLarge(HTTPClientError):
    """Represent HTTP 413 when the request body exceeds the application limit."""

    status_code = 413

    def __init__(self, max_size: int, actual_size: int, **kwargs: Any) -> None:
        kwargs.setdefault(
            'text',
            f'Maximum request body size {max_size} exceeded, actual body size {actual_size}',
        )
        super().__init__(**kwargs)
        self.max_size = max_size
        self.actual_size = actual_size


class HTTPRequestURITooLong(HTTPClientError):
    """Represent HTTP 414 URI Too Long."""

    status_code = 414


class HTTPUnsupportedMediaType(HTTPClientError):
    """Represent HTTP 415 Unsupported Media Type."""

    status_code = 415


class HTTPRequestRangeNotSatisfiable(HTTPClientError):
    """Represent HTTP 416 Range Not Satisfiable."""

    status_code = 416


class HTTPExpectationFailed(HTTPClientError):
    """Represent HTTP 417 Expectation Failed."""

    status_code = 417


class HTTPMisdirectedRequest(HTTPClientError):
    """Represent HTTP 421 Misdirected Request."""

    status_code = 421


class HTTPUnprocessableEntity(HTTPClientError):
    """Represent HTTP 422 Unprocessable Entity."""

    status_code = 422


class HTTPValidationFailure(HTTPUnprocessableEntity):
    """Carry normalized request validation errors in the stable JSON schema."""

    validation_failure_field_name: str = 'errors'

    def __init__(
        self,
        errors: ValidationErrorList,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self._errors = normalize_errors(errors, pop_useless_keys=False)
        if text is None:
            text = cast('Callable[..., str]', DEFAULT_JSON_ENCODER)(
                {self.validation_failure_field_name: self._errors},
                default=str,
            )
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type='application/json' if content_type is None else content_type,
        )

    @property
    def validation_errors(self) -> ValidationErrorList:
        """Return normalized Pydantic-v2 error details."""
        return self._errors


class HTTPFailedDependency(HTTPClientError):
    """Represent HTTP 424 Failed Dependency."""

    status_code = 424


class HTTPUpgradeRequired(HTTPClientError):
    """Represent HTTP 426 Upgrade Required."""

    status_code = 426


class HTTPPreconditionRequired(HTTPClientError):
    """Represent HTTP 428 Precondition Required."""

    status_code = 428


class HTTPTooManyRequests(HTTPClientError):
    """Represent HTTP 429 Too Many Requests."""

    status_code = 429


class HTTPRequestHeaderFieldsTooLarge(HTTPClientError):
    """Represent HTTP 431 Request Header Fields Too Large."""

    status_code = 431


class HTTPUnavailableForLegalReasons(HTTPClientError):
    """Represent HTTP 451 Unavailable For Legal Reasons."""

    status_code = 451

    def __init__(
        self,
        link: str | None,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self._link: str | None = None
        if link:
            self._link = link
            self.headers['Link'] = f'<{link}>; rel="blocked-by"'

    @property
    def link(self) -> str | None:
        """Return the optional legal-blocking reference URL."""
        return self._link


class HTTPServerError(HTTPError):
    """Abstract base for HTTP 5xx exceptions."""


class HTTPInternalServerError(HTTPServerError):
    """Represent HTTP 500 Internal Server Error."""

    status_code = 500


class HTTPNotImplemented(HTTPServerError):
    """Represent HTTP 501 Not Implemented."""

    status_code = 501


class HTTPBadGateway(HTTPServerError):
    """Represent HTTP 502 Bad Gateway."""

    status_code = 502


class HTTPServiceUnavailable(HTTPServerError):
    """Represent HTTP 503 Service Unavailable."""

    status_code = 503


class HTTPGatewayTimeout(HTTPServerError):
    """Represent HTTP 504 Gateway Timeout."""

    status_code = 504


class HTTPVersionNotSupported(HTTPServerError):
    """Represent HTTP 505 Version Not Supported."""

    status_code = 505


class HTTPVariantAlsoNegotiates(HTTPServerError):
    """Represent HTTP 506 Variant Also Negotiates."""

    status_code = 506


class HTTPInsufficientStorage(HTTPServerError):
    """Represent HTTP 507 Insufficient Storage."""

    status_code = 507


class HTTPNotExtended(HTTPServerError):
    """Represent HTTP 510 Not Extended."""

    status_code = 510


class HTTPNetworkAuthenticationRequired(HTTPServerError):
    """Represent HTTP 511 Network Authentication Required."""

    status_code = 511
