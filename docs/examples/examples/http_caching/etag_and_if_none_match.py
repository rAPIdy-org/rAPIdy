import hashlib

from rapidy import Rapidy
from rapidy.http import Header, HeaderName, HTTPNotModified, Response, get

@get('/')
async def handler(
    response: Response,
    if_none_match: str | None = Header(None, alias=HeaderName.if_none_match),
) -> str:
    content = 'success'  # <-- endpoint dynamic content

    etag_value = hashlib.md5(content.encode()).hexdigest()

    if if_none_match.strip('"') == etag_value:
        raise HTTPNotModified

    response.etag = etag_value
    response.headers[HeaderName.cache_control] = 'public, max-age=3600'

    return content

rapidy = Rapidy(http_route_handlers=[handler])