from rapidy import Rapidy

def cleanup() -> None:
    print('cleanup')

rapidy = Rapidy(on_cleanup=[cleanup])