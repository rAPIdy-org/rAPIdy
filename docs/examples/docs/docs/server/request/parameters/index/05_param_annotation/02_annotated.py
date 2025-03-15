from typing import Annotated
from rapidy.http import get, PathParam

@get('/{user_id}')
async def handler(
    user_id: Annotated[int, PathParam()],
) -> ...:
    ...