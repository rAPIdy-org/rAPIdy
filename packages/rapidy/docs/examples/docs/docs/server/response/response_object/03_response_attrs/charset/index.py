from rapidy.http import Response, get, Charset

@get('/')
async def handler() -> Response:
    return Response(
        charset=Charset.utf32,
        # or
        charset='utf32',
    )

@get('/')
async def handler(response: Response) -> ...:
    response.charset = Charset.utf32
    # or
    response.charset = 'utf32'
