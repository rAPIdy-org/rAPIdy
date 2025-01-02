from rapidy import Rapidy

async def async_cleanup(rapidy: Rapidy) -> None:
    print(f'async_cleanup, application: {rapidy}')

rapidy = Rapidy(on_cleanup=[async_cleanup])