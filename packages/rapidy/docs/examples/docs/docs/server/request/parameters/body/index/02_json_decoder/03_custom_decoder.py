from typing import Any
from rapidy.http import post, Body

def custom_json_decoder(data: str) -> ...:
    ...

@post('/')
async def handler(
    data: Any = Body(json_decoder=custom_json_decoder),
) -> ...: