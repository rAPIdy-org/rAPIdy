from pydantic import BaseModel, Field

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

@get(
    '/',
    response_by_alias=True,  # <-- default
)
async def handler() -> Result:
    return Result()  # {"someValue": "data"}

...

@get(
    '/',
    response_by_alias=False,
)
async def handler() -> Result:
    return Result()  # {"value": "data"}
