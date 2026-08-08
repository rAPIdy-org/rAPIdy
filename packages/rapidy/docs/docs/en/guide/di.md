# Dependency injection

rAPIdy exposes the supported DI surface from `rapidy.depends`. Application code does not need to import Dishka
directly, and rAPIdy itself consumes it through `rapidy-core`.

```python
from collections.abc import AsyncIterator
from dataclasses import dataclass

from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get


@dataclass(frozen=True)
class Settings:
    service_name: str = 'users'


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return Settings()

    @provide(scope=Scope.REQUEST)
    async def transaction(self) -> AsyncIterator[list[str]]:
        value: list[str] = []
        try:
            yield value
        finally:
            value.clear()


@get('/context')
async def context(settings: FromDI[Settings], transaction: FromDI[list[str]]) -> dict[str, str]:
    transaction.append('handled')
    return {'service': settings.service_name}


app = Rapidy(di_providers=[AppProvider()], http_route_handlers=[context])
```

The complete example is
[`examples/di.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/di.py).

## Scopes

- `Scope.APP`: one value for one application process. With four server workers there are four independent APP
  containers and four instances of each singleton.
- `Scope.REQUEST`: one value per HTTP request. Async-generator finalizers run after the response, including streaming
  completion or disconnect.
- `Scope.SESSION`: one value per accepted WebSocket connection. The context contains the current `WebSocket` and
  `Request`; finalizers run once on close, disconnect, or handler failure.

The root `Rapidy` application owns the container unless an external `di_container` is supplied. Mounted
`HTTPRouter` applications share the root request scope and do not create a second container.

## Injection sites

`FromDI[T]` works in HTTP handlers, middleware, controllers, and WebSocket handlers. `Request` and `WebSocket` can be
declared directly by type. Use `request.state.di_container` only for dynamic resolution that cannot be represented in a
typed signature.
