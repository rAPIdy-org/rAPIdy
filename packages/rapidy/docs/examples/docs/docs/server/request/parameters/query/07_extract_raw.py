async def extract_query(request: Request) -> MultiDictProxy[str]:
    return request.rel_url.query