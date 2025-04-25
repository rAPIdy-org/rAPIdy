from rapidy import Rapidy

root_app = Rapidy()
v1_app = Rapidy()
root_app.add_subapp('/v1', v1_app)

root_app.di_container  # AsyncContainer
v1_app.di_container  # None