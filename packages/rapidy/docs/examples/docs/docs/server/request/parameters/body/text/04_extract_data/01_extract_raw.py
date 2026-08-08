async def extract_body_text(request: Request) -> Optional[str]:
    if not request.body_exists:
        return None

    return await request.text()