async def extract_body_stream(request: Request) -> Optional[StreamReader]:
    if not request.body_exists:
        return None

    return request.content