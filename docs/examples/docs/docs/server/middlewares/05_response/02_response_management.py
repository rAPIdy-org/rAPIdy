from rapidy import Rapidy
from rapidy.http import middleware, StreamResponse, get, Request, Response
from rapidy.enums import ContentType
from rapidy.typedefs import CallNext

@middleware(response_content_type=ContentType.text_html)
async def hello_rapidy_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    try:
        return await call_next(request)
    except Exception:
        return Response(status=500)  # Content-Type='application/octet-stream'

@get('/')
async def handler() -> dict[str, str]:
    raise Exception

rapidy = Rapidy(middlewares=[hello_rapidy_middleware], http_route_handlers=[handler])