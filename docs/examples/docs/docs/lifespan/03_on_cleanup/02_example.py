from rapidy import Rapidy

def cleanup(rapidy: Rapidy) -> None:
    print(f'cleanup, application: {rapidy}')

rapidy = Rapidy(on_cleanup=[cleanup])