from __future__ import annotations

from rapidy._base_exceptions import RapidyHandlerException

__all__ = ('AllowHeadError', 'MethodAlreadyRegisteredError', 'MethodNotFoundInViewError')


class AllowHeadError(RapidyHandlerException):
    """Raised when a View cannot derive HEAD from a missing GET method."""

    message = (
        'Cannot automatically define the `head` method in `View` because the `get` method is not defined.'
        '\nThis is internal `rAPIdy` error, please open the issue - '
        'https://github.com/rAPIdy-org/rAPIdy/issues/new'
    )


class MethodNotFoundInViewError(RapidyHandlerException):
    """Raised when a requested View method is absent."""

    message = 'Failed to register View - method named `{method_name}` was not found.'


class MethodAlreadyRegisteredError(ValueError):
    """Raised when a View method is registered more than once."""


# NOTE(06-extraction-pipeline): handler/view validation wrappers join extraction there.
