from pydantic import BaseModel, Field

class Result(BaseModel):
    data: str = Field(max_length=10)

@post('/')
async def handler() -> Result:
    return Result(data='some_data')  # success response --> `{"data": "some_data"}`