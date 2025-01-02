async def extract_body_bytes(request: Request) -> Optional[bytes]:
    if not request.body_exists:
        return None

    return await request.read()