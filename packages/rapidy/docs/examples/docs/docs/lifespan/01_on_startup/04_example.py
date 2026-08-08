from rapidy import Rapidy

async def async_startup(rapidy: Rapidy) -> None:
    print(f'async_startup, application: {app}')

rapidy = Rapidy(on_startup=[async_startup])