from pydantic import BaseModel
from rapidy import Rapidy
from rapidy.http import Body, Request, Header, StreamResponse, middleware, post
from rapidy.typedefs import CallNext

TOKEN_REGEXP = '^[Bb]earer (?P<token>[A-Za-z0-9-_=.]*)'

class RequestBody(BaseModel):
    username: str
    password: str

class ResponseBody(BaseModel):
    hello: str = 'rapidy'

@middleware
async def get_bearer_middleware(
        request: Request,
        call_next: CallNext,
        bearer_token: str = Header(alias='Authorization', pattern=TOKEN_REGEXP),
) -> StreamResponse:
    # process token here ...
    return await call_next(request)

@post('/')
async def handler(body: RequestBody = Body()) -> ResponseBody:
    return ResponseBody()

app = Rapidy(middlewares=[get_bearer_middleware], http_route_handlers=[handler])
