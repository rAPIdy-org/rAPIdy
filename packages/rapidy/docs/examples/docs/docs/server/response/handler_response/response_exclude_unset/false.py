from pydantic import BaseModel, Field
from rapidy.http import get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

@get(
    '/',
    response_exclude_unset=False,  # <-- default
)
async def handler() -> Result:
    return Result(someAnotherValue='new_data')  # {"someValue": "data", "someAnotherValue": "new_data"}