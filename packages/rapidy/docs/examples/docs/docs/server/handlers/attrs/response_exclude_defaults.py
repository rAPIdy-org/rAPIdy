from pydantic import BaseModel, Field

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

@get(
    '/',
    exclude_defaults=False,  # <-- default
)
async def handler() -> Result:
    return Result()  # {"value": "data"}

...

@get(
    '/',
    exclude_defaults=True,
)
async def handler() -> Result:
    return Result()  # {}
