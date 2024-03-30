from rapidy import web

async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

app = web.Application()
app.add_routes([web.post('/', handler)])
