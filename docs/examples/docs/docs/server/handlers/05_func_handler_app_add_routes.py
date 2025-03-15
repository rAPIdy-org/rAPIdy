from rapidy import web, Rapidy

async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_routes([web.post('/', handler)])