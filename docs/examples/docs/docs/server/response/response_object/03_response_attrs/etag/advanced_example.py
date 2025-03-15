import hashlib
from rapidy.http import Header, HTTPNotModified, Response, get

@get('/')
async def handler(
    response: Response,
    if_none_match: str | None = Header(None, alias='If-None-Match'),
) -> str:
    content = 'success'

    # Generate ETag based on content
    etag_value = hashlib.md5(content.encode()).hexdigest()

    # Check If-None-Match
    if if_none_match and if_none_match == etag_value:
        raise HTTPNotModified

    response.etag = etag_value

    return content
