from typing import Any
from rapidy.http import Response, get

def custom_encoder(obj: Any) -> str:
    ...

@get('/')
async def handler() -> Response:
    return Response(
        body={'hello': 'rapidy!'},  # will be converted to a string by Rapidy's internal tools
        json_encoder=custom_encoder,  # Converts the obtained string above into a JSON object using the `custom_encoder` function
    )