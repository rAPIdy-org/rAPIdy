from rapidy.http import Response, get, HeaderName

@get('/')
async def handler(response: Response) -> str:
    content = 'success'  # <-- endpoint dynamic content

    response.headers[HeaderName.cache_control] = "public, max-age=600, must-revalidate"

    return content