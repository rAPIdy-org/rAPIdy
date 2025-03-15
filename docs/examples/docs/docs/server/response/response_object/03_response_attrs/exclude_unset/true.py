...
@get('/')
async def handler() -> Response:
    return Response(
        Result(someAnotherValue='new_data'),
        exclude_unset=True,
    )  # {"someAnotherValue": "new_data"}