async def extract_cookies(request: Request) -> Mapping[str, str]:
    return request.cookies