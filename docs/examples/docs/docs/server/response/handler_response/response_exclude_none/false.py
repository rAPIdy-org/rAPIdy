from pydantic import BaseModel, Field
from rapidy.http import get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    none_value: None = None

@get(
    '/',
    response_exclude_none=False,  # <-- default
)
async def handler() -> Result:
    return Result()  # {"someValue": "data", "none_value": null}