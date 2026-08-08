from rapidy.http import get, Response

@get('/')
async def handler(
    response: Response,  # <-- this response will be ignored
) -> Response:
    response.set_status(200)  # <-- `200` status will be ignored

    return Response(status=500)  # <-- new Response obj returned status `500`