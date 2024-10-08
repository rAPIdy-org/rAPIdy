from typing import Dict

from aiohttp.helpers import content_disposition_header

from rapidy import hdrs
from rapidy.enums import RequestBodyType
from rapidy.request_parameters import (
    Body,
    Cookie,
    Cookies,
    Header,
    Headers,
    PathParam,
    PathParams,
    QueryParam,
    QueryParams,
)


def create_content_type_header(content_type: str = 'text/plain') -> Dict[str, str]:
    return {
        hdrs.CONTENT_TYPE: content_type,
    }


def create_multipart_headers(
        part_name: str,
        content_type: str = 'text/plain',
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
    (Body(body_type=RequestBodyType.json), Body(body_type=RequestBodyType.x_www_form)),
)

body_params = (
    Body(body_type=RequestBodyType.json),
    Body(body_type=RequestBodyType.x_www_form),
    Body(body_type=RequestBodyType.multipart_form_data),
    Body(body_type=RequestBodyType.binary),
    Body(body_type=RequestBodyType.text),
)


BOUNDARY = '92101efb88714b6c9f43f7f06c6b58c7'
