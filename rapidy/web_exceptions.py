import warnings

from rapidy._version import AIOHTTP_VERSION_TUPLE
from rapidy.web_response import Response

if AIOHTTP_VERSION_TUPLE >= (3, 9, 0):
    from aiohttp.web_exceptions import HTTPMove as AioHTTPMove, NotAppKeyWarning
else:
    from aiohttp.web_exceptions import _HTTPMove as AioHTTPMove  # noqa: WPS440

import json
from typing import Any, Optional

from aiohttp.web_exceptions import (
    HTTPAccepted as AioHTTPAccepted,
    HTTPBadGateway as AioHTTPBadGateway,
    HTTPBadRequest as AioHTTPBadRequest,
    HTTPClientError as AioHTTPClientError,
    HTTPConflict as AioHTTPConflict,
    HTTPCreated as AioHTTPCreated,
    HTTPError as AioHTTPError,
    HTTPException as AioHTTPException,
    HTTPExpectationFailed as AioHTTPExpectationFailed,
    HTTPFailedDependency as AioHTTPFailedDependency,
    HTTPForbidden as AioHTTPForbidden,
    HTTPFound as AioHTTPFound,
    HTTPGatewayTimeout as AioHTTPGatewayTimeout,
    HTTPGone as AioHTTPGone,
    HTTPInsufficientStorage as AioHTTPInsufficientStorage,
    HTTPInternalServerError as AioHTTPInternalServerError,
    HTTPLengthRequired as AioHTTPLengthRequired,
    HTTPMethodNotAllowed as AioHTTPMethodNotAllowed,
    HTTPMisdirectedRequest as AioHTTPMisdirectedRequest,
    HTTPMovedPermanently as AioHTTPMovedPermanently,
    HTTPMultipleChoices as AioHTTPMultipleChoices,
    HTTPNetworkAuthenticationRequired as AioHTTPNetworkAuthenticationRequired,
    HTTPNoContent as AioHTTPNoContent,
    HTTPNonAuthoritativeInformation as AioHTTPNonAuthoritativeInformation,
    HTTPNotAcceptable as AioHTTPNotAcceptable,
    HTTPNotExtended as AioHTTPNotExtended,
    HTTPNotFound as AioHTTPNotFound,
    HTTPNotImplemented as AioHTTPNotImplemented,
    HTTPNotModified as AioHTTPNotModified,
    HTTPOk as AioHTTPOk,
    HTTPPartialContent as AioHTTPPartialContent,
    HTTPPaymentRequired as AioHTTPPaymentRequired,
    HTTPPermanentRedirect as AioHTTPPermanentRedirect,
    HTTPPreconditionFailed as AioHTTPPreconditionFailed,
    HTTPPreconditionRequired as AioHTTPPreconditionRequired,
    HTTPProxyAuthenticationRequired as AioHTTPProxyAuthenticationRequired,
    HTTPRedirection as AioHTTPRedirection,
    HTTPRequestEntityTooLarge as AioHTTPRequestEntityTooLarge,
    HTTPRequestHeaderFieldsTooLarge as AioHTTPRequestHeaderFieldsTooLarge,
    HTTPRequestRangeNotSatisfiable as AioHTTPRequestRangeNotSatisfiable,
    HTTPRequestTimeout as AioHTTPRequestTimeout,
    HTTPRequestURITooLong as AioHTTPRequestURITooLong,
    HTTPResetContent as AioHTTPResetContent,
    HTTPSeeOther as AioHTTPSeeOther,
    HTTPServerError as AioHTTPServerError,
    HTTPServiceUnavailable as AioHTTPServiceUnavailable,
    HTTPSuccessful as AioHTTPSuccessful,
    HTTPTemporaryRedirect as AioHTTPTemporaryRedirect,
    HTTPTooManyRequests as AioHTTPTooManyRequests,
    HTTPUnauthorized as AioHTTPUnauthorized,
    HTTPUnavailableForLegalReasons as AioHTTPUnavailableForLegalReasons,
    HTTPUnprocessableEntity as AioHTTPUnprocessableEntity,
    HTTPUnsupportedMediaType as AioHTTPUnsupportedMediaType,
    HTTPUpgradeRequired as AioHTTPUpgradeRequired,
    HTTPUseProxy as AioHTTPUseProxy,
    HTTPVariantAlsoNegotiates as AioHTTPVariantAlsoNegotiates,
    HTTPVersionNotSupported as AioHTTPVersionNotSupported,
)

from rapidy.media_types import ApplicationJSON
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
    'HTTPMove',
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
        'NotAppKeyWarning',
    ])

__all__ = tuple(__all)


############################################################
# base
############################################################

class HTTPException(AioHTTPException, Response):
    def __init__(
        self,
        *,
        headers: Optional[LooseHeaders] = None,
        reason: Optional[str] = None,
        body: Any = None,
        text: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        if body is not None:
            warnings.warn(
                'body argument is deprecated for http web exceptions',
                DeprecationWarning,
                stacklevel=1,
            )

        Response.__init__(  # type: ignore[call-arg]
            self,
            status=self.status_code,
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )

        Exception.__init__(self, self.reason)

        if self.body is None and not self.empty_body:
            self.text = f'{self.status}: {self.reason}'


class HTTPError(AioHTTPError, HTTPException):
    """Base class for exceptions with status codes in the 400s and 500s."""


class HTTPRedirection(AioHTTPRedirection, HTTPException):
    """Base class for exceptions with status codes in the 300s."""


class HTTPSuccessful(AioHTTPSuccessful, HTTPException):
    """Base class for exceptions with status codes in the 200s."""


class HTTPMove(AioHTTPMove, HTTPRedirection):
    pass


class HTTPServerError(AioHTTPServerError, HTTPError):
    pass


############################################################
# 2xx success
############################################################

class HTTPOk(AioHTTPOk, HTTPSuccessful):
    """200"""


class HTTPCreated(AioHTTPCreated, HTTPSuccessful):
    """201"""


class HTTPAccepted(AioHTTPAccepted, HTTPSuccessful):
    """202"""


class HTTPNonAuthoritativeInformation(AioHTTPNonAuthoritativeInformation, HTTPSuccessful):
    """203"""


class HTTPNoContent(AioHTTPNoContent, HTTPSuccessful):
    """204"""


class HTTPResetContent(AioHTTPResetContent, HTTPSuccessful):
    """205"""


class HTTPPartialContent(AioHTTPPartialContent, HTTPSuccessful):
    """206"""


############################################################
# 3xx redirection
############################################################

class HTTPMultipleChoices(AioHTTPMultipleChoices, HTTPMove):
    """300"""


class HTTPMovedPermanently(AioHTTPMovedPermanently, HTTPMove):
    """301"""


class HTTPFound(AioHTTPFound, HTTPMove):
    """302"""


class HTTPSeeOther(AioHTTPSeeOther, HTTPMove):
    """303"""


class HTTPNotModified(AioHTTPNotModified, HTTPRedirection):
    """304"""


class HTTPUseProxy(AioHTTPUseProxy, HTTPMove):
    """305"""


class HTTPTemporaryRedirect(AioHTTPTemporaryRedirect, HTTPMove):
    """307"""


class HTTPPermanentRedirect(AioHTTPPermanentRedirect, HTTPMove):
    """308"""


############################################################
# 4xx client error
############################################################

class HTTPClientError(AioHTTPClientError, HTTPError):
    pass


class HTTPBadRequest(AioHTTPBadRequest, HTTPClientError):
    """400"""


class HTTPUnauthorized(AioHTTPUnauthorized, HTTPClientError):
    """401"""


class HTTPPaymentRequired(AioHTTPPaymentRequired, HTTPClientError):
    """402"""


class HTTPForbidden(AioHTTPForbidden, HTTPClientError):
    """403"""


class HTTPNotFound(AioHTTPNotFound, HTTPClientError):
    """404"""


class HTTPMethodNotAllowed(AioHTTPMethodNotAllowed, HTTPClientError):
    """405"""


class HTTPNotAcceptable(AioHTTPNotAcceptable, HTTPClientError):
    """406"""


class HTTPProxyAuthenticationRequired(AioHTTPProxyAuthenticationRequired, HTTPClientError):
    """407"""


class HTTPRequestTimeout(AioHTTPRequestTimeout, HTTPClientError):
    """408"""


class HTTPConflict(AioHTTPConflict, HTTPClientError):
    """409"""


class HTTPGone(AioHTTPGone, HTTPClientError):
    """410"""


class HTTPLengthRequired(AioHTTPLengthRequired, HTTPClientError):
    """411"""


class HTTPPreconditionFailed(AioHTTPPreconditionFailed, HTTPClientError):
    """412"""


class HTTPRequestEntityTooLarge(AioHTTPRequestEntityTooLarge, HTTPClientError):
    """413"""


class HTTPRequestURITooLong(AioHTTPRequestURITooLong, HTTPClientError):
    """414"""


class HTTPUnsupportedMediaType(AioHTTPUnsupportedMediaType, HTTPClientError):
    """415"""


class HTTPRequestRangeNotSatisfiable(AioHTTPRequestRangeNotSatisfiable, HTTPClientError):
    """416"""


class HTTPExpectationFailed(AioHTTPExpectationFailed, HTTPClientError):
    """417"""


class HTTPMisdirectedRequest(AioHTTPMisdirectedRequest, HTTPClientError):
    """421"""


class HTTPUnprocessableEntity(AioHTTPUnprocessableEntity, HTTPClientError):
    """422"""


class HTTPValidationFailure(HTTPUnprocessableEntity):
    """422. Use it to catch user input errors."""

    def __init__(
            self,
            validation_failure_field_name: str,
            errors: ValidationErrorList,
            *,
            headers: Optional[LooseHeaders] = None,
            reason: Optional[str] = None,
            body: Any = None,
            text: Optional[str] = None,
            content_type: Optional[str] = None,
    ) -> None:
        self._errors = errors
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=json.dumps({validation_failure_field_name: errors}) if text is None else text,
            content_type=ApplicationJSON if content_type is None else content_type,
        )

    @property
    def validation_errors(self) -> ValidationErrorList:
        return self._errors


class HTTPFailedDependency(AioHTTPFailedDependency, HTTPClientError):
    """424"""


class HTTPUpgradeRequired(AioHTTPUpgradeRequired, HTTPClientError):
    """426"""


class HTTPPreconditionRequired(AioHTTPPreconditionRequired, HTTPClientError):
    """428"""


class HTTPTooManyRequests(AioHTTPTooManyRequests, HTTPClientError):
    """429"""


class HTTPRequestHeaderFieldsTooLarge(AioHTTPRequestHeaderFieldsTooLarge, HTTPClientError):
    """431"""


class HTTPUnavailableForLegalReasons(AioHTTPUnavailableForLegalReasons, HTTPClientError):
    """451"""


############################################################
# 5xx Server Error
############################################################

class HTTPInternalServerError(AioHTTPInternalServerError, HTTPServerError):
    """500"""


class HTTPNotImplemented(AioHTTPNotImplemented, HTTPServerError):
    """501"""


class HTTPBadGateway(AioHTTPBadGateway, HTTPServerError):
    """502"""


class HTTPServiceUnavailable(AioHTTPServiceUnavailable, HTTPServerError):
    """503"""


class HTTPGatewayTimeout(AioHTTPGatewayTimeout, HTTPServerError):
    """504"""


class HTTPVersionNotSupported(AioHTTPVersionNotSupported, HTTPServerError):
    """505"""


class HTTPVariantAlsoNegotiates(AioHTTPVariantAlsoNegotiates, HTTPServerError):
    """506"""


class HTTPInsufficientStorage(AioHTTPInsufficientStorage, HTTPServerError):
    """507"""


class HTTPNotExtended(AioHTTPNotExtended, HTTPServerError):
    """510"""


class HTTPNetworkAuthenticationRequired(AioHTTPNetworkAuthenticationRequired, HTTPServerError):
    """511"""
