from enum import Enum
from typing import Dict

from aiohttp.helpers import MimeType, parse_mimetype

__all__ = [
    'BodyType',
]


class BodyType(str, Enum):
    text = 'text'
    binary = 'binary'
    json = 'json'
    x_www_form = 'x_www_form'
    multipart_form_data = 'multipart_form_data'


class HTTPRequestParamType(str, Enum):
    path = 'path'
    query = 'query'
    header = 'header'
    cookie = 'cookie'
    body = 'body'


_body_type_content_type_map: Dict[BodyType, MimeType] = {
    BodyType.binary: parse_mimetype('application/octet-stream'),
    BodyType.text: parse_mimetype('text/*'),
    BodyType.json: parse_mimetype('application/json'),
    BodyType.x_www_form: parse_mimetype('application/x-www-form-urlencoded'),
    BodyType.multipart_form_data: parse_mimetype('multipart/form-data'),
}


def get_content_type_by_body_type(body_type: BodyType) -> MimeType:
    return _body_type_content_type_map[body_type]
