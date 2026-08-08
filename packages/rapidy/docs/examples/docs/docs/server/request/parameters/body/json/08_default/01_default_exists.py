from pydantic import BaseModel
from rapidy.http import post, Body

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData = Body('some_data'),
    # or
    data: BodyData = Body(default_factory=lambda: 'some_data'),
) -> ...: