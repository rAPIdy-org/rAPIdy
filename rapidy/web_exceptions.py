from __future__ import annotations

from aiohttp.typedefs import DEFAULT_JSON_ENCODER, LooseHeaders

from rapidy._client_errors import normalize_errors
from rapidy.version import AIOHTTP_VERSION_TUPLE

if AIOHTTP_VERSION_TUPLE >= (3, 9, 0):
    from aiohttp.web_exceptions import HTTPMove, NotAppKeyWarning

from typing import Any, Optional

from aiohttp.web_exceptions import (
    HTTPAccepted,
    HTTPBadGateway,
    HTTPBadRequest,
    HTTPClientError,
    HTTPConflict,
    HTTPCreated,
    HTTPError,
    HTTPException,
    HTTPExpectationFailed,
    HTTPFailedDependency,
    HTTPForbidden,
    HTTPFound,
    HTTPGatewayTimeout,
    HTTPGone,
    HTTPInsufficientStorage,
    HTTPInternalServerError,
    HTTPLengthRequired,
    HTTPMethodNotAllowed,
    HTTPMisdirectedRequest,
    HTTPMovedPermanently,
    HTTPMultipleChoices,
    HTTPNetworkAuthenticationRequired,
    HTTPNoContent,
    HTTPNonAuthoritativeInformation,
    HTTPNotAcceptable,
    HTTPNotExtended,
    HTTPNotFound,
    HTTPNotImplemented,
    HTTPNotModified,
    HTTPOk,
    HTTPPartialContent,
    HTTPPaymentRequired,
    HTTPPermanentRedirect,
    HTTPPreconditionFailed,
    HTTPPreconditionRequired,
    HTTPProxyAuthenticationRequired,
    HTTPRedirection,
    HTTPRequestEntityTooLarge,
    HTTPRequestHeaderFieldsTooLarge,
    HTTPRequestRangeNotSatisfiable,
    HTTPRequestTimeout,
    HTTPRequestURITooLong,
    HTTPResetContent,
    HTTPSeeOther,
    HTTPServerError,
    HTTPServiceUnavailable,
    HTTPSuccessful,
    HTTPTemporaryRedirect,
    HTTPTooManyRequests,
    HTTPUnauthorized,
    HTTPUnavailableForLegalReasons,
    HTTPUnprocessableEntity,
    HTTPUnsupportedMediaType,
    HTTPUpgradeRequired,
    HTTPUseProxy,
    HTTPVariantAlsoNegotiates,
    HTTPVersionNotSupported,
)

from rapidy.typedefs import ValidationErrorList

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
]

if AIOHTTP_VERSION_TUPLE >= (3, 9, 0):
    __all__ += [
        'HTTPMove',
        'NotAppKeyWarning',
    ]


class HTTPValidationFailure(HTTPUnprocessableEntity):
    """Exception raised for HTTP validation failure.

    This exception is used to report validation errors in HTTP requests. It inherits from
    `HTTPUnprocessableEntity` and returns a detailed error message in JSON format.

    Attributes:
        validation_failure_field_name (str): The name of the field that holds validation errors.
        _errors (ValidationErrorList): List of validation errors.

    Args:
        errors (ValidationErrorList): A list of validation errors.
        headers (Optional[LooseHeaders], optional): Custom headers for the HTTP response. Defaults to None.
        reason (Optional[str], optional): Reason phrase for the HTTP response. Defaults to None.
        body (Any, optional): The body content of the HTTP response. Defaults to None.
        text (Optional[str], optional): The text content of the HTTP response. Defaults to None.
        content_type (Optional[str], optional): The content type of the HTTP response. Defaults to 'application/json'.
    """

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
        self._errors = normalize_errors(errors)
        if text is None:
            text = DEFAULT_JSON_ENCODER({self.validation_failure_field_name: self._errors}, default=str)

        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type='application/json' if content_type is None else content_type,
        )

    @property
    def validation_errors(self) -> ValidationErrorList:
        """Return the validation errors.

        Returns:
            ValidationErrorList: The list of validation errors associated with the failure.
        """
        return self._errors
