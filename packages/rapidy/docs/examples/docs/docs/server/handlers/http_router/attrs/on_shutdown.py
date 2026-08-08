from rapidy.http import HTTPRouter

async def shutdown() -> None:
    print('shutdown')

router = HTTPRouter(
    path='/api',
    on_shutdown=[shutdown],
)