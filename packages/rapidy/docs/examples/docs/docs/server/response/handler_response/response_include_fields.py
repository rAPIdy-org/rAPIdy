from pydantic import BaseModel, Field
from rapidy.http import get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

@get(
    '/',
    response_include_fields={'value'},
)
async def handler() -> Result:
    return Result()  # {'someValue': 'data'}