async def extract_post_data(request: Request) -> Optional[MultiDictProxy[Union[str, bytes, FileField]]]:
    if not request.body_exists:
        return None

    return await request.post()