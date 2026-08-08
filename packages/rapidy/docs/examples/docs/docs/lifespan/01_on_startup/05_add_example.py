from rapidy import Rapidy

async def startup() -> None:
    print('startup')

rapidy = Rapidy()
rapidy.lifespan.on_startup.append(startup)