from rapidy.depends import make_container, Provider, provide, Scope

class MainProvider(Provider):
    # default component is used here

    @provide(scope=Scope.APP)
    def foo(self, a: int) -> float:
        return a/10

class AdditionalProvider(Provider):
    component = "X"

    @provide(scope=Scope.APP)
    def foo(self) -> int:
        return 1

# we will get error immediately during container creation, skip validation for demo needs
container = make_container(MainProvider(), AdditionalProvider(), skip_validation=True)
# retrieve from component "X"
container.get(int, component="X")  # value 1 would be returned
# retrieve from default component
container.get(float)  # raises NoFactoryError because int is in another component