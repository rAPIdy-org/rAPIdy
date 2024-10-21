import traceback
import warnings
from abc import ABC
from decimal import Decimal
from enum import Enum
from functools import partial
from json import JSONDecodeError
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Type, Union

from aiohttp import helpers
from aiohttp.abc import Request
from aiohttp.streams import StreamReader
from aiohttp.web_request import FileField
from multidict import MultiDict, MultiDictProxy, MultiMapping

from rapidy import hdrs
from rapidy._annotation_helpers import lenient_issubclass
from rapidy._client_errors import ClientError
from rapidy._request_param_field_info import ParamFieldInfo
from rapidy.enums import ContentType, HTTPRequestParamType
from rapidy.request_parameters import Body
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


async def extract_query(request: Request) -> MultiDict[str]:
    return request.rel_url.query


async def extract_body_stream(request: Request, body_field_info: Body) -> Optional[StreamReader]:
    if not request.body_exists:
        return None

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
        raise ExtractJsonError(json_decode_err_msg=json_decode_err.args[0])


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
                raise ExtractMultipartError(multipart_error=msg)

        warnings.warn(f'Failed to extract body data: \n{traceback.format_exc()}', stacklevel=2)
        raise ExtractBodyError(error='extraction error')

    return data


_http_simple_request_param_extractor_map: Dict[HTTPRequestParamType, ExtractFunction] = {
    HTTPRequestParamType.path: extract_path,
    HTTPRequestParamType.header: extract_headers,
    HTTPRequestParamType.cookie: extract_cookies,
    HTTPRequestParamType.query: extract_query,
}


def _get_body_extractor_by_annotation(annotation: Type[Any]) -> Optional[ExtractBodyFunction]:
    if lenient_issubclass(annotation, (str, int, float, Decimal, Enum)):
        return extract_body_text

    if lenient_issubclass(annotation, bytes):
        return extract_body_bytes

    if annotation == StreamReader:
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


def get_extractor(field_info: ParamFieldInfo) -> ExtractFunction:
    if field_info.http_request_param_type == HTTPRequestParamType.body:
        assert isinstance(field_info, Body)
        return get_body_extractor(field_info)

    return get_simple_param_extractor(field_info)


def get_simple_param_extractor(field_info: ParamFieldInfo) -> ExtractFunction:
    return _http_simple_request_param_extractor_map[field_info.http_request_param_type]


def get_body_extractor(body_field_info: Body) -> ExtractFunction:
    assert body_field_info.annotation

    expected_ctype = helpers.parse_mimetype(body_field_info.content_type)

    extractor = _get_body_extractor_by_annotation(body_field_info.annotation)
    if not extractor:
        extractor = _get_body_extractor_by_content_type(expected_ctype)

    if not body_field_info.check_content_type:
        return partial(extractor, body_field_info=body_field_info)

    return create_checked_type_extractor(extractor, body_field_info=body_field_info, expected_ctype=expected_ctype)


def create_checked_type_extractor(
        extractor: ExtractBodyFunction,
        body_field_info: Body,
        expected_ctype: helpers.MimeType,
) -> ExtractFunction:
    async def wrapped_extractor(request: Request) -> Optional[DictStrAny]:
        request_ctype = get_mimetype(request)

        if (
            request_ctype.type in (expected_ctype.type, '*')
            and request_ctype.subtype in (expected_ctype.subtype, '*')
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
    ctype = request.headers.get(hdrs.CONTENT_TYPE, '').lower()
    return helpers.parse_mimetype(ctype)
