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
    Header(None, alias=HeaderName.if_modified_since),
]

@get('/')
async def handler(
    response: Response,
    if_modified_since: IFModifiedSince,
) -> str:
    content = 'success'  # <-- endpoint dynamic content

    last_mod_time = datetime(2024, 2, 24, 12, 0, 0, tzinfo=timezone.utc)

    if if_modified_since and if_modified_since >= last_mod_time:
        raise HTTPNotModified

    response.last_modified = last_mod_time
    response.headers[HeaderName.cache_control] = 'public, max-age=3600'

    return content

rapidy = Rapidy(http_route_handlers=[handler])