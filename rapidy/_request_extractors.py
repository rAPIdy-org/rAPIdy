import sys
import traceback
from abc import ABC
from functools import partial
from json import JSONDecodeError
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Union

from aiohttp import helpers
from aiohttp.abc import Request
from aiohttp.streams import StreamReader
from aiohttp.web_request import FileField
from multidict import MultiDict, MultiDictProxy, MultiMapping

from rapidy import hdrs
from rapidy._client_errors import ClientError
from rapidy._request_param_field_info import ParamFieldInfo
from rapidy.request_enums import BodyType, get_content_type_by_body_type, HTTPRequestParamType
from rapidy.request_parameters import Body
from rapidy.typedefs import DictStrAny, DictStrStr

ExtractFunction = Callable[[Request], Awaitable[Any]]
ExtractBodyFunction = Callable[[Request, Body], Awaitable[Any]]


class ExtractError(ClientError, ABC):
    type = 'ExtractError'


class ExtractBodyError(ExtractError, ABC):
    msg_template = 'Failed to extract body data: {error}'


class IncorrectContentTypeError(ExtractBodyError, ABC):
    msg_template = 'Failed to extract body data. Expected Content-Type `{expected_ctype}` not `{request_ctype}`'


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

        _print_unknown_error(traceback.format_exc())
        raise ExtractBodyError(error='extraction error')

    return data


_http_simple_request_param_extractor_map: Dict[HTTPRequestParamType, ExtractFunction] = {
    HTTPRequestParamType.path: extract_path,
    HTTPRequestParamType.header: extract_headers,
    HTTPRequestParamType.cookie: extract_cookies,
    HTTPRequestParamType.query: extract_query,
}

_body_type_extractor_map: Dict[BodyType, ExtractBodyFunction] = {
    BodyType.text: extract_body_text,
    BodyType.binary: extract_body_bytes,
    BodyType.json: extract_body_json,
    BodyType.x_www_form: extract_post_data,
    BodyType.multipart_form_data: extract_post_data,
}


def get_extractor(field_info: ParamFieldInfo) -> ExtractFunction:
    if field_info.http_request_param_type == HTTPRequestParamType.body:
        assert isinstance(field_info, Body)
        return get_body_extractor(field_info)

    return get_simple_param_extractor(field_info)


def get_simple_param_extractor(field_info: ParamFieldInfo) -> ExtractFunction:
    return _http_simple_request_param_extractor_map[field_info.http_request_param_type]


def get_body_extractor(body_field_info: Body) -> ExtractFunction:
    assert body_field_info.annotation
    extractor: ExtractBodyFunction

    if body_field_info.annotation == StreamReader:
        extractor = extract_body_stream
    else:
        extractor = _body_type_extractor_map[body_field_info.body_type]

    if not body_field_info.check_content_type:
        return partial(extractor, body_field_info=body_field_info)

    return create_checked_type_extractor(extractor, body_field_info=body_field_info)


def create_checked_type_extractor(extractor: ExtractBodyFunction, body_field_info: Body) -> ExtractFunction:
    expected_ctype = get_content_type_by_body_type(body_field_info.body_type)

    async def wrapped_extractor(request: Request) -> Optional[DictStrAny]:
        request_ctype = get_mimetype(request)

        if request_ctype.type == expected_ctype.type:
            if request_ctype.subtype == expected_ctype.subtype or expected_ctype.subtype == '*':
                return await extractor(request, body_field_info)

        raise IncorrectContentTypeError(
            expected_ctype=f'{expected_ctype.type}/{expected_ctype.subtype}',
            request_ctype=f'{request_ctype.type}/{request_ctype.subtype}',
        )

    return wrapped_extractor


def get_mimetype(request: Request) -> helpers.MimeType:
    ctype = request.headers.get(hdrs.CONTENT_TYPE, '').lower()
    return helpers.parse_mimetype(ctype)


def _print_unknown_error(trace_msg: str) -> None:
    sys.stdout.write(f'Failed to extract body data:\n{trace_msg}')
