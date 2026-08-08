from typing import Any

@get('/')
async def handler_1(
    header_host: Any = Header(alias='Host')
) -> ...:
    # "0.0.0.0:8080"

@get('/')
async def handler_2(
    headers_data: Any = Headers()
) -> ...:
    # <CIMultiDictProxy('Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...')>