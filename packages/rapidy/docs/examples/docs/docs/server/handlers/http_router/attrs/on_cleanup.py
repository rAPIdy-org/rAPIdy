from rapidy.http import HTTPRouter

async def cleanup() -> None:
    print('cleanup')

router = HTTPRouter(
    path='/api',
    on_cleanup=[cleanup],
)