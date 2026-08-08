from rapidy import Rapidy

def startup() -> None:
    print('startup')

rapidy = Rapidy(on_startup=[startup])