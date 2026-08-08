from rapidy.http import get, Request

@get('/{user_id}')
async def handler(
    request: Request,
) -> ...:
    path_params = request.match_info  # dict[str, str]
    headers = request.headers  # CIMultiDictProxy[str]
    cookies = request.cookies  # Mapping[str, str]
    query_params = request.rel_url.query  # MultiDictProxy[str]
    json_body = await request.json()  # Any
    text_body = await request.text()  # str
    bytes_body = await request.read()  # bytes
    stream_body = request.content  # StreamReader