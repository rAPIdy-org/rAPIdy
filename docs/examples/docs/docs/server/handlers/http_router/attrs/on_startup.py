from rapidy.http import HTTPRouter

async def startup() -> None:
    print('startup')

router = HTTPRouter(
    path='/api',
    on_startup=[startup],
)