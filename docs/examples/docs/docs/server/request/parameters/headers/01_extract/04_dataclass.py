from dataclasses import dataclass
from rapidy.http import get, Headers

@dataclass
class HeadersData:
    host: str
    keep_alive: str  # cannot extract if header name is 'Keep-Alive'

@get('/')
async def handler(
    headers_data: HeadersData = Headers(),
) -> ...:
# {"errors": [{"type": "missing", "loc": ["header", "keep_alive" ], "msg": "Field required"}]}