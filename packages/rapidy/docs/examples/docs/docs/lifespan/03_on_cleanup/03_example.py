from rapidy import Rapidy

async def async_cleanup() -> None:
    print('async_cleanup')

rapidy = Rapidy(on_cleanup=[async_cleanup])