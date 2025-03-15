from rapidy import Rapidy

async def async_shutdown(rapidy: Rapidy) -> None:
    print(f'async_shutdown, application: {rapidy}')

rapidy = Rapidy(on_shutdown=[async_shutdown])