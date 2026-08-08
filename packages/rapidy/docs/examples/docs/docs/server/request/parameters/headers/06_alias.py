@get('/')
async def handler(
    headers_data: HeadersData = Headers(alias='SomeName'),  # <-- alias not working
) -> ...: