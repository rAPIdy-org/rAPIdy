from rapidy.http import post, Body

@post('/')
async def handler(
    bool_data: bool = Body(),
) -> ...: