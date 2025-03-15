from rapidy import Rapidy

async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.router.add_post('/', handler)
