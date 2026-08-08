from rapidy import Rapidy

async def cleanup() -> None:
    print('cleanup')

rapidy = Rapidy()
rapidy.lifespan.on_cleanup.append(cleanup)