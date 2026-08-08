from __future__ import annotations

import inspect
import json
from typing import Any, cast

import pytest
from multidict import CIMultiDict
from rapidy_core.exceptions import RapidyException

from rapidy import exceptions

EXPECTED_ALL = [
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

STATUS_CODES = {
    'HTTPOk': 200,
    'HTTPCreated': 201,
    'HTTPAccepted': 202,
    'HTTPNonAuthoritativeInformation': 203,
    'HTTPNoContent': 204,
    'HTTPResetContent': 205,
    'HTTPPartialContent': 206,
    'HTTPMultipleChoices': 300,
    'HTTPMovedPermanently': 301,
    'HTTPFound': 302,
    'HTTPSeeOther': 303,
    'HTTPNotModified': 304,
    'HTTPUseProxy': 305,
    'HTTPTemporaryRedirect': 307,
    'HTTPPermanentRedirect': 308,
    'HTTPBadRequest': 400,
    'HTTPUnauthorized': 401,
    'HTTPPaymentRequired': 402,
    'HTTPForbidden': 403,
    'HTTPNotFound': 404,
    'HTTPMethodNotAllowed': 405,
    'HTTPNotAcceptable': 406,
    'HTTPProxyAuthenticationRequired': 407,
    'HTTPRequestTimeout': 408,
    'HTTPConflict': 409,
    'HTTPGone': 410,
    'HTTPLengthRequired': 411,
    'HTTPPreconditionFailed': 412,
    'HTTPRequestEntityTooLarge': 413,
    'HTTPRequestURITooLong': 414,
    'HTTPUnsupportedMediaType': 415,
    'HTTPRequestRangeNotSatisfiable': 416,
    'HTTPExpectationFailed': 417,
    'HTTPMisdirectedRequest': 421,
    'HTTPUnprocessableEntity': 422,
    'HTTPValidationFailure': 422,
    'HTTPFailedDependency': 424,
    'HTTPUpgradeRequired': 426,
    'HTTPPreconditionRequired': 428,
    'HTTPTooManyRequests': 429,
    'HTTPRequestHeaderFieldsTooLarge': 431,
    'HTTPUnavailableForLegalReasons': 451,
    'HTTPInternalServerError': 500,
    'HTTPNotImplemented': 501,
    'HTTPBadGateway': 502,
    'HTTPServiceUnavailable': 503,
    'HTTPGatewayTimeout': 504,
    'HTTPVersionNotSupported': 505,
    'HTTPVariantAlsoNegotiates': 506,
    'HTTPInsufficientStorage': 507,
    'HTTPNotExtended': 510,
    'HTTPNetworkAuthenticationRequired': 511,
}


def make_exception(name: str) -> exceptions.HTTPException:
    cls = cast('type[exceptions.HTTPException]', getattr(exceptions, name))
    if issubclass(cls, exceptions.HTTPMove):
        return cls('/target')
    if cls is exceptions.HTTPMethodNotAllowed:
        return cls('POST', ['GET'])
    if cls is exceptions.HTTPRequestEntityTooLarge:
        return cls(1024, 2048)
    if cls is exceptions.HTTPUnavailableForLegalReasons:
        return cls('https://example.com')
    if cls is exceptions.HTTPValidationFailure:
        return cls([])
    return cls()


def test_all_matches_reference() -> None:
    assert exceptions.__all__ == EXPECTED_ALL
    assert len(exceptions.__all__) == 59
    assert 'NotAppKeyWarning' not in exceptions.__all__
    assert not hasattr(exceptions, 'NotAppKeyWarning')


def test_every_name_importable_and_instantiable() -> None:
    assert len(STATUS_CODES) == 52
    for name, status_code in STATUS_CODES.items():
        instance = make_exception(name)
        assert instance.status_code == status_code
        assert instance.status == status_code


@pytest.mark.parametrize(
    'factory',
    [
        exceptions.HTTPException,
        exceptions.HTTPSuccessful,
        exceptions.HTTPRedirection,
        exceptions.HTTPError,
        exceptions.HTTPClientError,
        exceptions.HTTPServerError,
        lambda: exceptions.HTTPMove('/target'),
    ],
)
def test_abstract_nodes_raise_runtime_error(factory: Any) -> None:
    with pytest.raises(RuntimeError, match='abstract exception'):
        factory()


def test_hierarchy_matrix() -> None:
    assert issubclass(exceptions.HTTPFound, exceptions.HTTPMove)
    assert issubclass(exceptions.HTTPMove, exceptions.HTTPRedirection)
    assert issubclass(exceptions.HTTPNotFound, exceptions.HTTPClientError)
    assert issubclass(exceptions.HTTPClientError, exceptions.HTTPError)
    assert issubclass(exceptions.HTTPInternalServerError, exceptions.HTTPServerError)
    assert issubclass(exceptions.HTTPServerError, exceptions.HTTPError)
    assert issubclass(exceptions.HTTPValidationFailure, exceptions.HTTPUnprocessableEntity)
    assert issubclass(exceptions.HTTPNotModified, exceptions.HTTPRedirection)
    assert not issubclass(exceptions.HTTPNotModified, exceptions.HTTPMove)
    assert issubclass(exceptions.HTTPOk, exceptions.HTTPSuccessful)
    assert issubclass(exceptions.HTTPException, Exception)
    assert not issubclass(exceptions.HTTPException, RapidyException)


def test_status_code_is_class_attribute() -> None:
    for name, status_code in STATUS_CODES.items():
        assert getattr(exceptions, name).status_code == status_code


def test_base_signature_keyword_only() -> None:
    exception = exceptions.HTTPNotFound(
        headers={'X-A': '1'},
        reason='Nope',
        text='gone',
        content_type='text/plain',
    )
    assert exception.headers['x-a'] == '1'
    assert exception.reason == 'Nope'
    with pytest.raises(TypeError):
        cast('Any', exceptions.HTTPNotFound)('positional')
    parameters = list(inspect.signature(exceptions.HTTPException.__init__).parameters.values())[1:]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters)


def test_default_body() -> None:
    exception = exceptions.HTTPNotFound()
    assert exception.reason == 'Not Found'
    assert exception.text == '404: Not Found'
    assert exception.body is None
    assert exception.content_type == 'text/plain'
    assert exceptions.HTTPNotFound(text='custom').text == 'custom'
    with pytest.raises(ValueError, match='Reason cannot contain'):
        exceptions.HTTPNotFound(reason='bad\nreason')


def test_empty_body_statuses() -> None:
    for cls in (exceptions.HTTPNoContent, exceptions.HTTPResetContent, exceptions.HTTPNotModified):
        exception = cls()
        assert exception.text is None
        assert exception.body is None
        assert exception.content_type is None


def test_headers_mutable() -> None:
    exception = exceptions.HTTPNotFound()
    assert isinstance(exception.headers, CIMultiDict)
    exception.headers['X-Custom'] = 'value'
    assert exception.headers['x-custom'] == 'value'


def test_move_family() -> None:
    found = exceptions.HTTPFound('/next')
    assert found.location == '/next'
    assert found.headers['Location'] == '/next'
    for location in ('', None):
        with pytest.raises(ValueError, match='need a location'):
            exceptions.HTTPFound(cast('Any', location))
    assert {
        cls.status_code
        for cls in (
            exceptions.HTTPMultipleChoices,
            exceptions.HTTPMovedPermanently,
            exceptions.HTTPFound,
            exceptions.HTTPSeeOther,
            exceptions.HTTPUseProxy,
            exceptions.HTTPTemporaryRedirect,
            exceptions.HTTPPermanentRedirect,
        )
    } == {300, 301, 302, 303, 305, 307, 308}


def test_method_not_allowed() -> None:
    exception = exceptions.HTTPMethodNotAllowed('post', ['HEAD', 'GET'])
    assert exception.headers['Allow'] == 'GET, HEAD'
    assert exception.method == 'POST'
    assert exception.allowed_methods == {'GET', 'HEAD'}


def test_entity_too_large() -> None:
    exception = exceptions.HTTPRequestEntityTooLarge(max_size=1024, actual_size=2048)
    assert exception.text == 'Maximum request body size 1024 exceeded, actual body size 2048'
    assert exception.max_size == 1024
    assert exception.actual_size == 2048
    assert exception.status_code == 413


def test_legal_reasons() -> None:
    blocked = exceptions.HTTPUnavailableForLegalReasons('https://example.com')
    assert blocked.headers['Link'] == '<https://example.com>; rel="blocked-by"'
    assert blocked.link == 'https://example.com'
    unlinked = exceptions.HTTPUnavailableForLegalReasons(None)
    assert 'Link' not in unlinked.headers
    assert unlinked.link is None


def test_unauthorized_no_www_authenticate() -> None:
    assert 'WWW-Authenticate' not in exceptions.HTTPUnauthorized().headers


def test_validation_failure_contract() -> None:
    raw_error = {
        'loc': ('body', 'field'),
        'msg': 'field required',
        'type': 'missing',
        'input': {},
        'url': 'https://errors.pydantic.dev/example',
    }
    exception = exceptions.HTTPValidationFailure([raw_error])
    body = json.loads(exception.text or '')
    assert exception.validation_errors == [raw_error]
    assert body['errors'][0]['loc'] == ['body', 'field']
    assert body['errors'][0]['input'] == {}
    assert body['errors'][0]['url'] == raw_error['url']
    assert exception.content_type == 'application/json'
    assert exception.status_code == 422


def test_validation_failure_field_name_override() -> None:
    class DetailFailure(exceptions.HTTPValidationFailure):
        validation_failure_field_name = 'detail'

    exception = DetailFailure([{'loc': ('body',), 'msg': 'bad', 'type': 'value_error'}])
    assert list(json.loads(exception.text or '')) == ['detail']
