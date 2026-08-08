...
@get('/')
async def handler() -> Response:
    return Response(
        Result(),
        exclude_none=True,
    )  # {"someValue": "data"}