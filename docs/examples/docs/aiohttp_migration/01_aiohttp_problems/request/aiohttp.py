from aiohttp import web

router = web.RouteTableDef()

@router.get('/hello')
async def hello(request: web.Request) -> web.Response:  # `request` required
    return web.json_response({'hello': 'aiohttp'})

app = web.Application()
app.add_routes(router)