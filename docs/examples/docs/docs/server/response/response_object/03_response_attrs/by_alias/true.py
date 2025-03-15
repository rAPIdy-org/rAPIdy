from pydantic import BaseModel, Field
from rapidy.http import get, Response

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

@get('/',)
async def handler() -> Response:
    return Response(
        Result(),
        by_alias=True,  # <-- default
    )  # {"someValue": "data"}