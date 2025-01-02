from rapidy.http import middleware, Request, StreamResponse, Header
from rapidy.typedefs import CallNext

TOKEN_REGEXP = '^[Bb]earer (?P<token>[A-Za-z0-9-_=.]*)'

@middleware
async def get_bearer_middleware(
        request: Request,
        call_next: CallNext,
        bearer_token: str = Header(alias='Authorization', pattern=TOKEN_REGEXP),
) -> StreamResponse:
    # process token here...
    return await call_next(request)