from pydantic import BaseModel
from rapidy.http import get, PathParams

class PathData(BaseModel):
    user_id: str
    user_data: str

@get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = PathParams(),
) -> ...: