from typing import Dict

from aiohttp.helpers import content_disposition_header

from rapidy import hdrs
from rapidy.media_types import TextPlain


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
