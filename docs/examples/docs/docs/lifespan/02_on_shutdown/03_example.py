from rapidy import Rapidy

async def async_shutdown() -> None:
    print('async_shutdown')

rapidy = Rapidy(on_shutdown=[async_shutdown])