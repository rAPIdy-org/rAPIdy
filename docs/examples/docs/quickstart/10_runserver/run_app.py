from rapidy import Rapidy, run_app
from rapidy.http import post

@post('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_http_router(handler)

if __name__ == '__main__':
    run_app(rapidy)
