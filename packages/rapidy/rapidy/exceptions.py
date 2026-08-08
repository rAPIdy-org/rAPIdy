from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from http import HTTPStatus
from typing import Any, cast

from multidict import CIMultiDict
from rapidy_core.client_errors import normalize_errors
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.exceptions import RapidyException

from rapidy.typedefs import LooseHeaders, ValidationErrorList

__all__ = (
    'ASGIProtocolError',
    'HTTPBadRequest',
    'HTTPException',
    'HTTPMethodNotAllowed',
    'HTTPNotFound',
    'HTTPPermanentRedirect',
    'HTTPRequestEntityTooLarge',
    'HTTPValidationFailure',
    'ResponseDuplicateBodyError',
    'ResponseEncodeError',
    'RouteConflictError',
)


class ASGIProtocolError(RapidyException):
    """Raised when an ASGI peer sends an unexpected event."""


class RouteConflictError(RapidyException):
    """Raised when a method/path pair is registered twice."""


class ResponseDuplicateBodyError(RapidyException):
    """Raised when both compatibility body inputs are provided."""


class ResponseEncodeError(RapidyException):
    """Reserved for full response serialization in milestone 10."""


# TODO(09-exceptions-full): replace with the complete §5.7 hierarchy without changing constructors.  # noqa: FIX002
class HTTPException(Exception):  # noqa: N818
    """Minimal HTTP error contract used by the matcher and dispatcher."""

    status_code: int = -1

    def __init__(
        self,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.reason = reason or HTTPStatus(self.status_code).phrase
        self.text = text if text is not None else f'{self.status_code}: {self.reason}'
        self.body = body if body is not None else self.text
        self.content_type = content_type or 'text/plain'
        if headers is None:
            self.headers: CIMultiDict[str] = CIMultiDict()
        elif isinstance(headers, Mapping):
            self.headers = CIMultiDict(headers)
        else:
            self.headers = CIMultiDict(
                (
                    key.decode('latin-1') if isinstance(key, bytes) else key,
                    value.decode('latin-1') if isinstance(value, bytes) else value,
                )
                for key, value in headers
            )
        super().__init__(self.text)


class HTTPNotFound(HTTPException):
    """Resource path was not registered."""

    status_code = HTTPStatus.NOT_FOUND


class HTTPBadRequest(HTTPException):
    """The request metadata is malformed."""

    status_code = HTTPStatus.BAD_REQUEST


class HTTPPermanentRedirect(HTTPException):
    """Redirect permanently while preserving the request method."""

    status_code = HTTPStatus.PERMANENT_REDIRECT

    def __init__(
        self,
        location: str,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.location = location
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self.headers['Location'] = location


class HTTPRequestEntityTooLarge(HTTPException):
    """The request body exceeded the configured application limit."""

    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self, max_size: int, actual_size: int, **kwargs: Any) -> None:
        self.max_size = max_size
        self.actual_size = actual_size
        kwargs.setdefault(
            'text',
            f'Maximum request body size {max_size} exceeded, actual body size {actual_size}',
        )
        super().__init__(**kwargs)


class HTTPValidationFailure(HTTPException):
    """Carry normalized request validation errors in the stable 422 schema."""

    # TODO(09-exceptions-full): inherit from HTTPUnprocessableEntity without changing this contract.  # noqa: FIX002
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    validation_failure_field_name: str = 'errors'

    def __init__(
        self,
        errors: ValidationErrorList,
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
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


class HTTPMethodNotAllowed(HTTPException):
    """Resource exists, but not for the requested method."""

    status_code = HTTPStatus.METHOD_NOT_ALLOWED

    def __init__(
        self,
        method: str,
        allowed_methods: Iterable[str],
        *,
        headers: LooseHeaders | None = None,
        reason: str | None = None,
        body: Any | None = None,
        text: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.method = method
        self.allowed_methods = set(allowed_methods)
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=text,
            content_type=content_type,
        )
        self.headers['Allow'] = ', '.join(sorted(self.allowed_methods))
