import datetime
from rapidy.http import get, Response

@get('/')
async def handler() -> ...:
    response = Response()
    # or
    response.last_modified = datetime.datetime(2024, 2, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
    # or
    response.last_modified = 'Wed, 21 Oct 2024 07:28:00 GMT'
    ...

@get('/')
async def handler(response: Response) -> ...:
    # or
    response.last_modified = datetime.datetime(2024, 2, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
    # or
    response.last_modified = 'Wed, 21 Oct 2024 07:28:00 GMT'
    ...