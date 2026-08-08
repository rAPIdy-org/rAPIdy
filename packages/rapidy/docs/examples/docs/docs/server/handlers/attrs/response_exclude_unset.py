from pydantic import BaseModel, Field

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

@get(
    '/',
    exclude_unset=False,  # <-- default
)
async def handler() -> Result:
    Result(someAnotherValue='new_data')  # {"someValue": "data", "someAnotherValue": "new_data"}

...

@get(
    '/',
    exclude_unset=True,
)
async def handler() -> Result:
    return Result(someAnotherValue='new_data')  # {"someAnotherValue": "new_data"}