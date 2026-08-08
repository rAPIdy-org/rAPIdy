from dataclasses import dataclass
from rapidy.http import get, PathParams

@dataclass
class PathData:
    user_id: str
    user_data: str

@get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = PathParams(),
) -> ...: