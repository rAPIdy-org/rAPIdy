import hashlib
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator
from rapidy import Rapidy
from rapidy.http import Header, HeaderName, HTTPNotModified, Response, get

def parse_http_date(value: str) -> datetime:
    return datetime.strptime(value, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)

IFModifiedSince = Annotated[
    datetime | None,
    BeforeValidator(parse_http_date),
    Header(None, alias='If-Modified-Since'),
]
IFNoneMatch = Annotated[
    str | None,
    BeforeValidator(lambda x: x.strip('"')),
    Header(None, alias='If-None-Match'),
]

@get('/')
async def handler(
        response: Response,
        if_modified_since: IFModifiedSince,
        if_none_match: IFNoneMatch,
) -> str:
    content = 'success'  # <-- endpoint dynamic content

    last_mod_time = datetime(2024, 2, 24, 12, 0, 0, tzinfo=timezone.utc)
    etag_value = hashlib.md5(content.encode()).hexdigest()
    expire_time = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    if if_none_match == etag_value:
        raise HTTPNotModified

    if if_modified_since and if_modified_since >= last_mod_time:
        raise HTTPNotModified

    response.etag = etag_value
    response.last_modified = last_mod_time
    response.headers[HeaderName.cache_control] = "public, max-age=3600, must-revalidate"
    response.headers[HeaderName.expires] = expire_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return content

rapidy = Rapidy(http_route_handlers=[handler])