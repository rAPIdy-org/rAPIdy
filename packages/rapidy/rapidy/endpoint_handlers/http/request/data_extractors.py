import traceback
import warnings
from abc import ABC
from collections.abc import Awaitable, Callable, Mapping
from json import JSONDecodeError
from typing import Any, cast

from multidict import CIMultiDictProxy, MultiDictProxy
from rapidy_core.annotation_checkers import lenient_issubclass
from rapidy_core.client_errors import ClientError
from rapidy_core.enums import ContentType, HeaderName, HTTPRequestParamType
from rapidy_core.parameters.http import Body, RequestParamFieldInfo
from rapidy_core.typedefs import DictStrAny, DictStrStr

from rapidy import helpers
from rapidy.exceptions import HTTPException
from rapidy.request import FileField, Request

__all__ = (
    'ExtractBodyError',
    'ExtractBodyFunction',
    'ExtractError',
    'ExtractFunction',
    'ExtractJsonError',
    'ExtractMultipartError',
    'IncorrectContentTypeError',
    'create_checked_type_extractor',
    'extract_body_bytes',
    'extract_body_json',
    'extract_body_text',
    'extract_cookies',
    'extract_headers',
    'extract_path',
    'extract_post_data',
    'extract_query',
    'get_body_extractor',
    'get_extractor',
    'get_mimetype',
    'get_simple_param_extractor',
)

type ExtractFunction = Callable[[Request], Awaitable[Any]]
type ExtractBodyFunction = Callable[[Request, Body], Awaitable[Any]]


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


async def extract_path(request: Request) -> DictStrStr:
    """Extract matched path parameters."""
    return dict(request.path_params)


async def extract_headers(request: Request) -> CIMultiDictProxy[str]:
    """Extract the read-only request headers."""
    return request.headers


async def extract_cookies(request: Request) -> Mapping[str, str]:
    """Extract the read-only cookie mapping."""
    return request.cookies


async def extract_query(request: Request) -> MultiDictProxy[str]:
    """Extract query parameters while preserving repeated keys."""
    return request.query


async def extract_body_bytes(request: Request, body_field_info: Body) -> bytes | None:  # noqa: ARG001
    """Extract a present body as bytes."""
    if not request.body_exists:
        return None
    return await request.read()


async def extract_body_text(request: Request, body_field_info: Body) -> str | None:  # noqa: ARG001
    """Extract a present body as text."""
    if not request.body_exists:
        return None
    return await request.text()


async def extract_body_json(request: Request, body_field_info: Body) -> DictStrAny | None:
    """Extract a present body with the marker's JSON decoder."""
    if not request.body_exists:
        return None
    try:
        return cast('DictStrAny', await request.json(loads=body_field_info.json_decoder))
    except JSONDecodeError as json_decode_error:
        raise ExtractJsonError(json_decode_err_msg=json_decode_error.msg) from json_decode_error
    except ValueError as value_error:
        raise ExtractJsonError(json_decode_err_msg='Invalid JSON value') from value_error
    except RecursionError as recursion_error:
        raise ExtractJsonError(json_decode_err_msg='JSON nesting is too deep') from recursion_error


async def extract_post_data(
    request: Request,
    body_field_info: Body,  # noqa: ARG001
) -> MultiDictProxy[str | bytes | FileField] | None:
    """Extract urlencoded or multipart form data."""
    if not request.body_exists:
        return None
    try:
        return await request.post()
    except HTTPException:
        # ASGI body-limit failures are rendered by the application, not converted into 422.
        raise
    except Exception as extraction_error:
        if extraction_error.args:
            message = extraction_error.args[0]
            if isinstance(message, str) and 'boundary' in message:
                raise ExtractMultipartError(multipart_error=message) from extraction_error
        warnings.warn(f'Failed to extract body data: \n{traceback.format_exc()}', stacklevel=2)
        raise ExtractBodyError(error='extraction error') from extraction_error


_http_simple_request_param_extractor_map: dict[HTTPRequestParamType, ExtractFunction] = {
    HTTPRequestParamType.path: extract_path,
    HTTPRequestParamType.header: extract_headers,
    HTTPRequestParamType.cookie: extract_cookies,
    HTTPRequestParamType.query: extract_query,
}


def _get_body_extractor_by_annotation(annotation: type[Any]) -> ExtractBodyFunction | None:
    if lenient_issubclass(annotation, bytes):
        return extract_body_bytes
    return None


def _get_body_extractor_by_content_type(content_type: helpers.MimeType) -> ExtractBodyFunction:
    content_type_value = f'{content_type.type}/{content_type.subtype}'
    if content_type_value == ContentType.json:
        return extract_body_json
    if content_type_value in (ContentType.x_www_form, ContentType.m_part_form_data):
        return extract_post_data
    if content_type.type == 'text':
        return extract_body_text
    return extract_body_bytes


def get_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    """Select the wire extractor for prepared request metadata."""
    if field_info.param_type == HTTPRequestParamType.body:
        assert isinstance(field_info, Body)  # noqa: S101
        return get_body_extractor(field_info)
    return get_simple_param_extractor(field_info)


def get_simple_param_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    """Select a non-body source extractor."""
    return _http_simple_request_param_extractor_map[field_info.param_type]


def get_body_extractor(body_field_info: Body) -> ExtractFunction:
    """Select and optionally content-type-check a body extractor."""
    assert body_field_info.annotation  # noqa: S101
    expected_content_type = helpers.parse_mimetype(str(body_field_info.content_type))
    extractor = _get_body_extractor_by_annotation(body_field_info.annotation)
    if extractor is None:
        extractor = _get_body_extractor_by_content_type(expected_content_type)
    if not body_field_info.check_content_type:
        async def unchecked_extractor(request: Request) -> Any:
            return await extractor(request, body_field_info)

        return unchecked_extractor
    return create_checked_type_extractor(
        extractor,
        body_field_info=body_field_info,
        expected_ctype=expected_content_type,
    )


def create_checked_type_extractor(
    extractor: ExtractBodyFunction,
    body_field_info: Body,
    expected_ctype: helpers.MimeType,
) -> ExtractFunction:
    """Wrap a body extractor with exact or wildcard MIME matching."""

    async def wrapped_extractor(request: Request) -> Any:
        request_ctype = get_mimetype(request)
        if (
            (request_ctype.type == expected_ctype.type or expected_ctype.type == '*')  # noqa: PLR1714
            and (
                request_ctype.subtype == expected_ctype.subtype  # noqa: PLR1714
                or expected_ctype.subtype == '*'
            )
        ):
            return await extractor(request, body_field_info)

        if not request_ctype.type and not request_ctype.subtype:
            error = (
                '`Content-Type` header cannot be empty. '
                f'Expected: `{expected_ctype.type}/{expected_ctype.subtype}`'
            )
        else:
            error = (
                f'Expected Content-Type `{expected_ctype.type}/{expected_ctype.subtype}` '
                f'not `{request_ctype.type}/{request_ctype.subtype}`'
            )
        raise IncorrectContentTypeError(error=error)

    return wrapped_extractor


def get_mimetype(request: Request) -> helpers.MimeType:
    """Parse the raw Content-Type header without applying Request defaults."""
    content_type = request.headers.get(HeaderName.content_type, '').lower()
    return helpers.parse_mimetype(content_type)
