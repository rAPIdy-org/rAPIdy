from rapidy.http import get, Headers

@get('/')
async def handler(
    headers_data: dict[str, str] = Headers(),
) -> ...:
# {Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...'}