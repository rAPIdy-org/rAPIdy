async def extract_path(request: Request) -> dict[str, str]:
    return dict(request.match_info)