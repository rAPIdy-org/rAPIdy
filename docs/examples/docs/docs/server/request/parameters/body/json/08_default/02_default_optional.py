from pydantic import BaseModel
from rapidy.http import post, Body

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData | None = Body(),
    # or
    data: Optional[BodyData] = Body(),
    # or
    data: Union[BodyData, None] = Body(),
) -> ...: