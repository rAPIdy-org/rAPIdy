async def extract_headers(request: Request) -> CIMultiDictProxy[str]:
    return request.headers