from decimal import Decimal
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import JsonBody

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
    request: web.Request,
    positive: Annotated[int, JsonBody(gt=0)],
    non_negative: Annotated[int, JsonBody(ge=0)],
    negative: Annotated[int, JsonBody(lt=0)],
    non_positive: Annotated[int, JsonBody(le=0)],
    even: Annotated[int, JsonBody(multiple_of=2)],
    love_for_pydantic: Annotated[float, JsonBody(allow_inf_nan=True)],
    short: Annotated[str, JsonBody(min_length=3)],
    long: Annotated[str, JsonBody(max_length=10)],
    regex: Annotated[str, JsonBody(pattern=r'^\d*$')],
    precise: Annotated[Decimal, JsonBody(max_digits=5, decimal_places=2)],
) -> web.Response:
    return web.Response()

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)