from __future__ import annotations

import traceback
import warnings
from abc import ABC
from functools import partial
from json import JSONDecodeError
from typing import Any, Awaitable, Callable, Dict, Mapping, Type, TYPE_CHECKING

from aiohttp import helpers
from aiohttp.abc import Request

from rapidy._client_errors import ClientError
from rapidy.annotation_checkers import lenient_issubclass
from rapidy.endpoint_handlers.http.annotation_checkers import is_stream_reader
from rapidy.enums import ContentType, HeaderName, HTTPRequestParamType
from rapidy.parameters.http import Body, RequestParamFieldInfo
from rapidy.typedefs import DictStrAny, DictStrStr

if TYPE_CHECKING:
    from aiohttp.streams import StreamReader
    from aiohttp.web_request import FileField
    from multidict import MultiDictProxy, MultiMapping

ExtractFunction = Callable[[Request], Awaitable[Any]]
ExtractBodyFunction = Callable[[Request, Body], Awaitable[Any]]


class ExtractError(ClientError, ABC):
    """Base class for errors that occur during data extraction.

    Attributes:
        type (str): The type of error.
    """

    type = 'ExtractError'


class ExtractBodyError(ExtractError, ABC):
    """Error raised when extracting body data fails.

    Attributes:
        msg_template (str): Template for the error message.
    """

    msg_template = 'Failed to extract body data: {error}'


class IncorrectContentTypeError(ExtractBodyError, ABC):
    """Error raised when the content type is incorrect during body extraction."""


class ExtractJsonError(ExtractBodyError):
    """Error raised when extracting JSON data fails.

    Attributes:
        msg_template (str): Template for the error message with specific details about the JSON decode error.
    """

    msg_template = 'Failed to extract body data as Json: {json_decode_err_msg}'


class ExtractMultipartError(ExtractBodyError):
    """Error raised when extracting multipart data fails.

    Attributes:
        msg_template (str): Template for the error message with details about the multipart extraction failure.
    """

    msg_template = 'Failed to extract body data as Multipart: {multipart_error}'


async def extract_path(request: Request) -> DictStrStr:
    """Extracts path parameters from the request.

    Args:
        request (Request): The request object.

    Returns:
        DictStrStr: A dictionary of path parameters.
    """
    return dict(request.match_info)


async def extract_headers(request: Request) -> MultiMapping[str]:
    """Extracts headers from the request.

    Args:
        request (Request): The request object.

    Returns:
        MultiMapping[str]: A mapping of header names to header values.
    """
    return request.headers


async def extract_cookies(request: Request) -> Mapping[str, str]:
    """Extracts cookies from the request.

    Args:
        request (Request): The request object.

    Returns:
        Mapping[str, str]: A dictionary of cookie names to cookie values.
    """
    return request.cookies


async def extract_query(request: Request) -> MultiDictProxy[str]:
    """Extracts query parameters from the request.

    Args:
        request (Request): The request object.

    Returns:
        MultiDictProxy[str]: A mapping of query parameter names to values.
    """
    return request.rel_url.query


async def extract_body_stream(request: Request, body_field_info: Body) -> StreamReader:  # noqa: ARG001
    """Extracts the body content as a stream.

    Args:
        request (Request): The request object.
        body_field_info (Body): Information about the body field to extract.

    Returns:
        StreamReader: A stream reader for the body content.
    """
    return request.content


async def extract_body_bytes(request: Request, body_field_info: Body) -> bytes | None:  # noqa: ARG001
    """Extracts the body content as bytes.

    Args:
        request (Request): The request object.
        body_field_info (Body): Information about the body field to extract.

    Returns:
        Optional[bytes]: The body content as bytes, or None if no body exists.
    """
    if not request.body_exists:
        return None

    return await request.read()


async def extract_body_text(request: Request, body_field_info: Body) -> str | None:  # noqa: ARG001
    """Extracts the body content as text.

    Args:
        request (Request): The request object.
        body_field_info (Body): Information about the body field to extract.

    Returns:
        Optional[str]: The body content as text, or None if no body exists.
    """
    if not request.body_exists:
        return None

    return await request.text()


async def extract_body_json(request: Request, body_field_info: Body) -> DictStrAny | None:
    """Extracts the body content as JSON.

    Args:
        request (Request): The request object.
        body_field_info (Body): Information about the body field to extract.

    Returns:
        Optional[DictStrAny]: The parsed JSON body, or None if no body exists.

    Raises:
        ExtractJsonError: If there is an error parsing the JSON body.
    """
    if not request.body_exists:
        return None

    try:
        return await request.json(loads=body_field_info.json_decoder)
    except JSONDecodeError as json_decode_err:
        raise ExtractJsonError(json_decode_err_msg=json_decode_err.args[0]) from json_decode_err


async def extract_post_data(
    request: Request,
    body_field_info: Body,  # noqa: ARG001
) -> MultiDictProxy[str | bytes | FileField] | None:
    """Extracts POST data from the request.

    Args:
        request (Request): The request object.
        body_field_info (Body): Information about the body field to extract.

    Returns:
        Optional[MultiDictProxy[Union[str, bytes, FileField]]]: The extracted POST data, or None if no data exists.

    Raises:
        ExtractBodyError: If there is an error extracting the body data.
        ExtractMultipartError: If there is an error with multipart data extraction.
    """
    if not request.body_exists:
        return None

    try:
        data = await request.post()
    except Exception as extractor_value_error:
        if extractor_value_error.args:
            msg = extractor_value_error.args[0]
            if 'boundary' in msg:
                raise ExtractMultipartError(multipart_error=msg) from extractor_value_error

        warnings.warn(f'Failed to extract body data: \n{traceback.format_exc()}', stacklevel=2)
        raise ExtractBodyError(error='extraction error') from extractor_value_error

    return data


_http_simple_request_param_extractor_map: Dict[HTTPRequestParamType, ExtractFunction] = {
    HTTPRequestParamType.path: extract_path,
    HTTPRequestParamType.header: extract_headers,
    HTTPRequestParamType.cookie: extract_cookies,
    HTTPRequestParamType.query: extract_query,
}


def _get_body_extractor_by_annotation(annotation: Type[Any]) -> ExtractBodyFunction | None:
    """Gets the body extractor function based on the annotation type.

    Args:
        annotation (Type[Any]): The annotation type for the body field.

    Returns:
        Optional[ExtractBodyFunction]: The extractor function, or None if not found.
    """
    if lenient_issubclass(annotation, bytes):
        return extract_body_bytes

    if is_stream_reader(annotation):
        return extract_body_stream

    return None


def _get_body_extractor_by_content_type(content_type: helpers.MimeType) -> ExtractBodyFunction:
    """Gets the body extractor function based on the content type.

    Args:
        content_type (helpers.MimeType): The content type of the request body.

    Returns:
        ExtractBodyFunction: The appropriate extractor function based on the content type.
    """
    content_type_str = f'{content_type.type}/{content_type.subtype}'

    if content_type_str == ContentType.json:
        return extract_body_json

    if content_type_str in (ContentType.x_www_form, ContentType.m_part_form_data):
        return extract_post_data

    if content_type.type == 'text':
        return extract_body_text

    return extract_body_bytes


def get_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    """Gets the extractor function based on the field information.

    Args:
        field_info (RequestParamFieldInfo): The field information to determine the extractor.

    Returns:
        ExtractFunction: The appropriate extractor function.
    """
    if field_info.param_type == HTTPRequestParamType.body:
        assert isinstance(field_info, Body)  # noqa: S101
        return get_body_extractor(field_info)

    return get_simple_param_extractor(field_info)


def get_simple_param_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    """Gets the extractor function for simple parameters (path, header, cookie, query).

    Args:
        field_info (RequestParamFieldInfo): The field information for the simple parameter.

    Returns:
        ExtractFunction: The appropriate extractor function for the simple parameter.
    """
    return _http_simple_request_param_extractor_map[field_info.param_type]


def get_body_extractor(body_field_info: Body) -> ExtractFunction:
    """Gets the body extractor function for a given body field.

    Args:
        body_field_info (Body): Information about the body field.

    Returns:
        ExtractFunction: The appropriate body extractor function.
    """
    assert body_field_info.annotation  # noqa: S101

    expected_ctype = helpers.parse_mimetype(body_field_info.content_type)

    extractor = _get_body_extractor_by_annotation(body_field_info.annotation)
    if not extractor:
        extractor = _get_body_extractor_by_content_type(expected_ctype)

    if not body_field_info.check_content_type:
        return partial(extractor, body_field_info=body_field_info)  # type: ignore[call-arg]

    return create_checked_type_extractor(extractor, body_field_info=body_field_info, expected_ctype=expected_ctype)


def create_checked_type_extractor(
    extractor: ExtractBodyFunction,
    body_field_info: Body,
    expected_ctype: helpers.MimeType,
) -> ExtractFunction:
    """Creates an extractor function that checks content type before extracting body data.

    Args:
        extractor (ExtractBodyFunction): The base extractor function.
        body_field_info (Body): Information about the body field.
        expected_ctype (helpers.MimeType): The expected content type.

    Returns:
        ExtractFunction: The wrapped extractor function with content type check.
    """

    async def wrapped_extractor(request: Request) -> DictStrAny | None:
        request_ctype = get_mimetype(request)

        if (
            (request_ctype.type == expected_ctype.type or expected_ctype.type == '*')  # noqa: PLR1714
            and (request_ctype.subtype == expected_ctype.subtype or expected_ctype.subtype == '*')  # noqa: PLR1714
        ):
            return await extractor(request, body_field_info)

        if not request_ctype.type and not request_ctype.subtype:
            error = f'`Content-Type` header cannot be empty. Expected: `{expected_ctype.type}/{expected_ctype.subtype}`'
        else:
            error = (
                f'Expected Content-Type `{expected_ctype.type}/{expected_ctype.subtype}` '
                f'not `{request_ctype.type}/{request_ctype.subtype}`'
            )

        raise IncorrectContentTypeError(error=error)

    return wrapped_extractor


def get_mimetype(request: Request) -> helpers.MimeType:
    """Gets the mimetype of the request.

    Args:
        request (Request): The request object.

    Returns:
        helpers.MimeType: The parsed mimetype of the request.
    """
    ctype = request.headers.get(HeaderName.content_type, '').lower()
    return helpers.parse_mimetype(ctype)
