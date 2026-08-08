@get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = PathParams(alias='SomeName'),  # <-- alias not working
) -> ...: