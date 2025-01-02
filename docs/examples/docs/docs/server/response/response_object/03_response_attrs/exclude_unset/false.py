from pydantic import BaseModel, Field
from rapidy.http import Response, get

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

@get('/')
async def handler() -> Response:
    return Response(
        Result(someAnotherValue='new_data'),
        exclude_unset=False,  # <-- default
    )  # {"someValue": "data", "someAnotherValue": "new_data"}