from pydantic import BaseModel, Field
from rapidy.http import Response, get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

@get('/')
async def handler() -> Response:
    return Response(
        Result(),
        exclude_defaults=False,  # <-- default
    )  # {"value": "data"}