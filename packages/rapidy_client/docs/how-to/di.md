# Dependency injection and `HttpApp`

`rapidy-client` uses the DI primitives exposed by `rapidy-core`. Dishka is a
regular transitive dependency; there is no separate `[di]` extra to install.
`HttpApp` is the small composition root that creates one application-scoped
client for every component and owns their lifecycle.

```python
from rapidy_core.di import Component
from rapidy_client import Response, UpstreamConfig
from rapidy_client.di import HttpApp
from rapidy_client.schema import controller, get

BILLING = Component("billing")
ORDERS = Component("orders")


@controller("/billing")
class BillingApi:
    @get("/health")
    async def health(self) -> Response:
        raise NotImplementedError


app = HttpApp(
    upstreams={
        BILLING: UpstreamConfig(base_url="https://billing.example"),
        ORDERS: UpstreamConfig(base_url="https://orders.example"),
    },
    controllers={BillingApi: BILLING},
)

async with app:
    api = await app.controller(BillingApi)
    response = await api.health()
```

Components qualify clients of the same Python type. A declaration deliberately
has no `upstream=` setting: the composition root decides which client binds to
it, so the same controller can be reused in another environment.

## Domain services and custom providers

Application services remain ordinary classes. Declare their dependencies with
the native `FromComponent` and `FromDI` annotations, register a regular core
provider, and pass it through `di_providers`.

```python
from typing import Annotated

from rapidy_core.di import Component, FromComponent, FromDI, Provider, Scope
from rapidy_client import HttpClient

type BillingClient = Annotated[HttpClient, FromComponent(BILLING)]


class AuditLog:
    pass


class BillingService:
    def __init__(self, client: BillingClient, audit: FromDI[AuditLog]) -> None:
        self.client = client
        self.audit = audit


domain = Provider()
domain.provide(AuditLog, scope=Scope.APP)
domain.provide(BillingService, scope=Scope.APP)

app = HttpApp(
    upstreams={BILLING: UpstreamConfig(base_url="https://billing.example")},
    di_providers=(domain,),
)

async with app:
    service = await app.container.get(BillingService)
```

For a functional declaration, use
`RapidyClientProvider.endpoint(endpoint, provides=Key, component=BILLING)`.
`RapidyClientProvider.controller(...)` provides the equivalent explicit
controller binding.

`HttpApp` creates its container only on `async with`, eagerly validates its
upstreams and registered controllers, and closes every owned client on exit.
Do not keep a client or bound controller after the context closes. Controllers
should not declare or mutate a public `self.client`: the binder's private
implementation state is not application state. Keep domain state in explicit
service classes.
