...
@get('/')
async def handler() -> Response:
    return Response(
        Result(),
        exclude_defaults=True,
    )  # {}