from pydantic import BaseModel, Field
from rapidy.http import Response, get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    none_value: None = None

@get('/')
async def handler() -> Response:
    return Response(
        Result(),
        exclude_none=False,  # <-- default
    )  # {"someValue": "data", "none_value": null}