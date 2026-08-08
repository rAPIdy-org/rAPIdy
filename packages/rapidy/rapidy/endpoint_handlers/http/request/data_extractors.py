from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable
from typing import Any, TYPE_CHECKING

from rapidy_core.client_errors import ClientError

if TYPE_CHECKING:
    from rapidy.request import Request

__all__ = (
    'ExtractBodyError',
    'ExtractBodyFunction',
    'ExtractError',
    'ExtractFunction',
    'ExtractJsonError',
    'ExtractMultipartError',
    'IncorrectContentTypeError',
)

type ExtractFunction = Callable[[Request], Awaitable[Any]]
type ExtractBodyFunction = Callable[[Request, Any], Awaitable[Any]]


class ExtractError(ClientError, ABC):
    """Base error produced while extracting request data."""

    type = 'ExtractError'


class ExtractBodyError(ExtractError, ABC):
    """Base request-body extraction error."""

    msg_template = 'Failed to extract body data: {error}'


class IncorrectContentTypeError(ExtractBodyError, ABC):
    """Raised when a request body has an unexpected content type."""


class ExtractJsonError(ExtractBodyError):
    """Raised when JSON decoding fails."""

    msg_template = 'Failed to extract body data as Json: {json_decode_err_msg}'


class ExtractMultipartError(ExtractBodyError):
    """Raised when multipart decoding fails."""

    msg_template = 'Failed to extract body data as Multipart: {multipart_error}'
