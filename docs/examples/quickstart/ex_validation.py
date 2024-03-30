import re

from pydantic import BaseModel
from rapidy import web
from rapidy.typedefs import HandlerType

TOKEN_REGEXP = re.compile('^[Bb]earer (?P<token>[A-Za-z0-9-_=.]*)')

class RequestBody(BaseModel):
    username: str
    password: str

class ResponseBody(BaseModel):
    hello: str = 'rapidy'

@web.middleware
async def get_bearer_middleware(
        request: web.Request,
        handler: HandlerType,
        bearer_token: str = web.Header(alias='Authorization', regex=TOKEN_REGEXP),
) -> web.StreamResponse:
    # process token here ...
    return await handler(request)

async def handler(body: RequestBody = web.Body()) -> ResponseBody:
    return ResponseBody()

app = web.Application(middlewares=[get_bearer_middleware])
app.add_routes([web.post('/', handler)])
