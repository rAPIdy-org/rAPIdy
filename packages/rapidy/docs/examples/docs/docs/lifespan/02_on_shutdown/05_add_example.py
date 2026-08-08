from rapidy import Rapidy

async def shutdown() -> None:
    print('shutdown')

rapidy = Rapidy()
rapidy.lifespan.on_shutdown.append(shutdown)