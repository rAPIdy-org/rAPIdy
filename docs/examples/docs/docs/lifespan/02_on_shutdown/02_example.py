from rapidy import Rapidy

def shutdown(rapidy: Rapidy) -> None:
    print(f'shutdown, application: {rapidy}')

rapidy = Rapidy(on_shutdown=[shutdown])