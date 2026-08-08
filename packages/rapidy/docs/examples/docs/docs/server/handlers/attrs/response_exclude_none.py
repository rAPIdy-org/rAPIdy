from pydantic import BaseModel, Field

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    none_value: None = None

@get(
    '/',
    exclude_none=False,  # <-- default
)
async def handler() -> Result:
    return Result()  # {"someValue": "data", "none_value": null}

...

@get(
    '/',
    exclude_none=True,
)
async def handler() -> Result:
    return Result()  # {"someValue": "data"}
