from datetime import datetime, timezone
from rapidy import Rapidy
from rapidy.http import Response, get, HeaderName

@get('/')
async def handler(response: Response) -> str:
    content = 'success'  # <-- endpoint dynamic content

    expire_time = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    response.headers[HeaderName.expires] = expire_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return content

rapidy = Rapidy(http_route_handlers=[handler])