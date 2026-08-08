from rapidy.http import post, Body

@post('/')
async def handler(
    int_data: int = Body(),
) -> ...: