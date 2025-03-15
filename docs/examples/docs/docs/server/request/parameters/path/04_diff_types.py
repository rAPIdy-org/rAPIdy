@get('/{user_id}/{user_data}')
async def handler(
    user_id: str = PathParam(),
    path_data: PathData = PathParams(),
) -> ...: