from datetime import datetime, timezone
from typing import Annotated
from pydantic import BeforeValidator
from rapidy.http import Header, HTTPNotModified, Response, get

def parse_http_date(value: str) -> datetime:
    return datetime.strptime(value, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)

IFModifiedSince = Annotated[
    datetime | None,
    BeforeValidator(parse_http_date),
    Header(None, alias='If-Modified-Since'),
]

@get('/')
async def handler(
    response: Response,
    if_modified_since: IFModifiedSince,
) -> str:
    last_mod_time = datetime(2024, 2, 24, 12, 0, 0, tzinfo=timezone.utc)

    # Check if the client sent the `If-Modified-Since` header
    if if_modified_since and if_modified_since >= last_mod_time:
        raise HTTPNotModified

    response.last_modified = last_mod_time  # Set the last modified date
    return 'success'
