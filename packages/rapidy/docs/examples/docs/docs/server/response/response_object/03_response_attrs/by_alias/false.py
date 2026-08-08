...
@get('/')
async def handler() -> Response:
    return Response(
        Result(),
        by_alias=False,
    )  # {"value": "data"}