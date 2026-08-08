from pydantic import BaseModel, Field
from rapidy.http import get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

@get(
    '/',
    response_by_alias=True,  # <-- default
)
async def handler() -> Result:
    return Result()  # {"someValue": "data"}