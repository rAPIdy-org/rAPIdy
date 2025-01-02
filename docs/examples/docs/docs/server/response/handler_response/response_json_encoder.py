from typing import Any
from rapidy.http import get

def custom_encoder(obj: Any) -> str:
    ...

@get(
    '/',
    response_json_encoder=custom_encoder,
)
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy!'}  # will be converted to a string by Rapidy's internal tools
