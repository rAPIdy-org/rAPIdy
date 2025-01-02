from rapidy.http import post, Body

@post('/')
async def handler(
    user_data: bytes = Body(),
    # also you can use pydantic validation
    user_data: bytes = Body(min_length=1),
) -> ...: