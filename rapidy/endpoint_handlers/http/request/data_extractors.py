import traceback
import warnings
from abc import ABC
from functools import partial
from json import JSONDecodeError
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Type, Union

from aiohttp import helpers
from aiohttp.abc import Request
from aiohttp.streams import StreamReader
from aiohttp.web_request import FileField
from multidict import MultiDictProxy, MultiMapping

from rapidy._client_errors import ClientError
from rapidy.annotation_checkers import lenient_issubclass
from rapidy.endpoint_handlers.http.annotation_checkers import is_stream_reader
from rapidy.enums import ContentType, HeaderName, HTTPRequestParamType
from rapidy.parameters.http import Body, RequestParamFieldInfo
from rapidy.typedefs import DictStrAny, DictStrStr

ExtractFunction = Callable[[Request], Awaitable[Any]]
ExtractBodyFunction = Callable[[Request, Body], Awaitable[Any]]


class ExtractError(ClientError, ABC):
    type = 'ExtractError'


class ExtractBodyError(ExtractError, ABC):
    msg_template = 'Failed to extract body data: {error}'


class IncorrectContentTypeError(ExtractBodyError, ABC):
    pass


class ExtractJsonError(ExtractBodyError):
    msg_template = 'Failed to extract body data as Json: {json_decode_err_msg}'


class ExtractMultipartError(ExtractBodyError):
    msg_template = 'Failed to extract body data as Multipart: {multipart_error}'


async def extract_path(request: Request) -> DictStrStr:
    return dict(request.match_info)


async def extract_headers(request: Request) -> MultiMapping[str]:
    return request.headers


async def extract_cookies(request: Request) -> Mapping[str, str]:
    return request.cookies


async def extract_query(request: Request) -> MultiDictProxy[str]:
    return request.rel_url.query


async def extract_body_stream(request: Request, body_field_info: Body) -> StreamReader:
    return request.content


async def extract_body_bytes(request: Request, body_field_info: Body) -> Optional[bytes]:
    if not request.body_exists:
        return None

    return await request.read()


async def extract_body_text(request: Request, body_field_info: Body) -> Optional[str]:
    if not request.body_exists:
        return None

    return await request.text()


async def extract_body_json(request: Request, body_field_info: Body) -> Optional[DictStrAny]:
    if not request.body_exists:
        return None

    try:
        return await request.json(loads=body_field_info.json_decoder)
    except JSONDecodeError as json_decode_err:
        raise ExtractJsonError(json_decode_err_msg=json_decode_err.args[0]) from json_decode_err


async def extract_post_data(
        request: Request,
        body_field_info: Body,
) -> Optional[MultiDictProxy[Union[str, bytes, FileField]]]:
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


def _get_body_extractor_by_annotation(annotation: Type[Any]) -> Optional[ExtractBodyFunction]:
    if lenient_issubclass(annotation, bytes):
        return extract_body_bytes

    if is_stream_reader(annotation):
        return extract_body_stream

    return None


def _get_body_extractor_by_content_type(content_type: helpers.MimeType) -> ExtractBodyFunction:
    content_type_str = f'{content_type.type}/{content_type.subtype}'

    if content_type_str == ContentType.json:
        return extract_body_json

    if content_type_str in (ContentType.x_www_form, ContentType.m_part_form_data):
        return extract_post_data

    if content_type.type == 'text':
        return extract_body_text

    return extract_body_bytes


def get_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    if field_info.param_type == HTTPRequestParamType.body:
        assert isinstance(field_info, Body)
        return get_body_extractor(field_info)

    return get_simple_param_extractor(field_info)


def get_simple_param_extractor(field_info: RequestParamFieldInfo) -> ExtractFunction:
    return _http_simple_request_param_extractor_map[field_info.param_type]


def get_body_extractor(body_field_info: Body) -> ExtractFunction:
    assert body_field_info.annotation

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
    async def wrapped_extractor(request: Request) -> Optional[DictStrAny]:
        request_ctype = get_mimetype(request)

        if (
            (request_ctype.type == expected_ctype.type or expected_ctype.type == '*')
            and (request_ctype.subtype == expected_ctype.subtype or expected_ctype.subtype == '*')
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
    ctype = request.headers.get(HeaderName.content_type, '').lower()
    return helpers.parse_mimetype(ctype)
