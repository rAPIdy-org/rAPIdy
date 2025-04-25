from rapidy.depends import provide, Provider, Scope

class FooProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def c(self) -> int:
        return 1