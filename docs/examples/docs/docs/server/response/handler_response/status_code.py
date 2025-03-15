from http import HTTPStatus
from rapidy.http import get

@get(
    '/',
    status_code=201,
)
async def handler() -> ...:
    ...

@get(
    '/',
    status_code=HTTPStatus.CREATED,
)
async def handler() -> ...:
    ...
