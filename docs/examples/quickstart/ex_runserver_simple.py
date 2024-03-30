from rapidy import web

async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

app = web.Application()
app.add_routes([web.post('/', handler)])

if __name__ == '__main__':
    web.run_app(app)