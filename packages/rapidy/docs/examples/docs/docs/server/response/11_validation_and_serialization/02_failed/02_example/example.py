from pydantic import BaseModel, Field

class Result(BaseModel):
    data: str = Field(max_length=10)

@post('/')
async def handler() -> Result:
    return {'data': 'another_data'}  # <-- will raise err