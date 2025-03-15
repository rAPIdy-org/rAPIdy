from rapidy import Rapidy

def shutdown() -> None:
    print('shutdown')

rapidy = Rapidy(on_shutdown=[shutdown])