from rapidy import Rapidy

def startup(rapidy: Rapidy) -> None:
    print(f'startup, application: {app}')

rapidy = Rapidy(on_startup=[startup])