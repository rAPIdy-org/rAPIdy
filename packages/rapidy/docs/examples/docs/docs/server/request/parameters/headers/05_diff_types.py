@get('/')
async def handler(
    host: str = Header(alias='Host'),
    headers_data: HeadersData = Headers(),
) -> ...: