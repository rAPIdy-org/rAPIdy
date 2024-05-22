from rapidy._client_errors import _normalize_errors
from rapidy.version import AIOHTTP_VERSION_TUPLE

if AIOHTTP_VERSION_TUPLE >= (3, 9, 0):
    from aiohttp.web_exceptions import HTTPMove, NotAppKeyWarning

import json
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

from rapidy.typedefs import LooseHeaders, ValidationErrorList

__all = [
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
    __all.extend([
        'HTTPMove',
        'NotAppKeyWarning',
    ])

__all__ = tuple(__all)


class HTTPValidationFailure(HTTPUnprocessableEntity):
    validation_failure_field_name: str = 'errors'

    def __init__(
            self,
            errors: ValidationErrorList,
            *,
            headers: Optional[LooseHeaders] = None,
            reason: Optional[str] = None,
            body: Any = None,
            text: Optional[str] = None,
            content_type: Optional[str] = None,
    ) -> None:
        self._errors = _normalize_errors(errors)
        if text is None:
            text = json.dumps({self.validation_failure_field_name: self._errors}, default=str)

        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type='application/json' if content_type is None else content_type,
        )

    @property
    def validation_errors(self) -> ValidationErrorList:
        return self._errors
