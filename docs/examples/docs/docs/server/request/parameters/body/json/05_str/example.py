from rapidy.http import post, Body

@post('/')
async def handler(
    string_data: str = Body(),
) -> ...: