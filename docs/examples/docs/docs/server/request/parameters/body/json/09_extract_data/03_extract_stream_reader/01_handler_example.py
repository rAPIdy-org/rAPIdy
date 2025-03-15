from rapidy import StreamReader
from rapidy.http import post, Body

@post('/')
async def handler(
    user_data: StreamReader = Body(),
) -> ...: