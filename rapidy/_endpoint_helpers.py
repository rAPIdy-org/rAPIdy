from concurrent.futures import Executor
from typing import Dict, Optional, Union

from aiohttp.helpers import MimeType, parse_mimetype

from rapidy import web_response
from rapidy.enums import ContentType, RequestBodyType

_request_body_type_content_type_map: Dict[RequestBodyType, MimeType] = {
    RequestBodyType.binary: parse_mimetype(ContentType.stream),
    RequestBodyType.text: parse_mimetype('text/*'),
    RequestBodyType.json: parse_mimetype(ContentType.json),
    RequestBodyType.x_www_form: parse_mimetype(ContentType.x_www_form),
    RequestBodyType.multipart_form_data: parse_mimetype(ContentType.m_part_form_data),
}


def get_content_type_by_request_body_type(body_type: RequestBodyType) -> MimeType:
    return _request_body_type_content_type_map[body_type]


def create_response(
        content_type: Union[str, ContentType],
        charset: str,
        zlib_executor: Optional[Executor],
        zlib_executor_size: Optional[int],
) -> web_response.Response:
    return web_response.Response(
        content_type=content_type,
        charset=charset,
        zlib_executor=zlib_executor,
        zlib_executor_size=zlib_executor_size,
    )
