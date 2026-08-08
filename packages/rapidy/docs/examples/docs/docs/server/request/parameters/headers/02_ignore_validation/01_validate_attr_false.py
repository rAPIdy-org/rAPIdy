from multidict import CIMultiDictProxy
from rapidy.http import get, Header, Headers

@get('/')
async def handler_1(
    header_host: str = Header(alias='Host', validate=False)
) -> ...:
    # "0.0.0.0:8080"

@get('/')
async def handler_2(
    headers_data: CIMultiDictProxy[str] = Headers(validate=False)
) -> ...:
    # <CIMultiDictProxy('Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...')>