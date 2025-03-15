from rapidy import Rapidy
from rapidy.http import middleware, StreamResponse, get, Request
from rapidy.enums import ContentType
from rapidy.typedefs import CallNext

@middleware(response_content_type=ContentType.text_html)
async def hello_rapidy_middleware(request: Request, call_next: CallNext) -> StreamResponse | str:
    try:
        return await call_next(request)
    except Exception:
        return 'server error'  # Content-Type='text/html'

@get('/')
async def handler() -> dict[str, str]:
    raise Exception

rapidy = Rapidy(middlewares=[hello_rapidy_middleware], http_route_handlers=[handler])