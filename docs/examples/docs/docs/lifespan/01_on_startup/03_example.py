from rapidy import Rapidy

async def async_startup() -> None:
    print('async_startup')

rapidy = Rapidy(on_startup=[async_startup])