from typing import Any

def custom_encoder(obj: Any) -> str:
    ...

@get(
    '/',
    response_json_encoder=custom_encoder,  # Converts the obtained string above into a JSON object using the `custom_encoder` function
)
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy!'}  # will be converted to a string by Rapidy's internal tools
