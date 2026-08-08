from rapidy.http import post, Body

@post('/')
async def handler(
    data: str = Body(),
) -> ...: