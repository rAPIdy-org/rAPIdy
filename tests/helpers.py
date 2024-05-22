from typing import Dict

from aiohttp.helpers import content_disposition_header

from rapidy import hdrs
from rapidy.media_types import TextPlain
from rapidy.request._enums import BodyType
from rapidy.request.parameters import Body, PathParam, PathParams, Header, Headers, Cookie, Cookies, QueryParam, \
    QueryParams


def create_content_type_header(content_type: str = TextPlain) -> Dict[str, str]:
    return {
        hdrs.CONTENT_TYPE: content_type,
    }


def create_multipart_headers(
        part_name: str,
        content_type: str = TextPlain,
        content_disposition_quote_fields: bool = True,
        content_disposition_charset: str = 'utf-8',
) -> Dict[str, str]:
    return {
        hdrs.CONTENT_DISPOSITION: content_disposition_header(
            disptype='form-data',
            quote_fields=content_disposition_quote_fields,
            _charset=content_disposition_charset,
            name=part_name,
        ),
        hdrs.CONTENT_TYPE: content_type,
    }


type_tuple_params = (
    (PathParam, PathParams),
    (Header, Headers),
    (Cookie, Cookies),
    (QueryParam, QueryParams),
    (Body(body_type=BodyType.json), Body(body_type=BodyType.x_www_form)),
)

body_params = (
    Body(body_type=BodyType.json),
    Body(body_type=BodyType.x_www_form),
    Body(body_type=BodyType.multipart_form_data),
    Body(body_type=BodyType.binary),
    Body(body_type=BodyType.text),
)


BOUNDARY = '92101efb88714b6c9f43f7f06c6b58c7'
