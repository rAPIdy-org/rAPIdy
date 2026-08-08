from __future__ import annotations

from typing import Annotated, assert_type

from rapidy_client import HttpClient, Response
from rapidy_client.di import HttpApp, provide_controller, provide_endpoint
from rapidy_client.schema import controller, get
from rapidy_core.di import Component, FromComponent, FromDI, Provider

BILLING = Component("billing")
type BillingClient = Annotated[HttpClient, FromComponent(BILLING)]


class DomainDependency:
    pass


class BillingService:
    def __init__(
        self,
        client: BillingClient,
        dependency: FromDI[DomainDependency],
    ) -> None:
        self.client = client
        self.dependency = dependency


@controller("/billing")
class BillingApi:
    @get("/health")
    async def health(self) -> Response:
        raise NotImplementedError


@get("/health")
async def health_endpoint() -> Response:
    raise NotImplementedError


class HealthEndpointKey:
    pass


async def check(app: HttpApp) -> None:
    controller_provider = provide_controller(BillingApi, component=BILLING)
    endpoint_provider = provide_endpoint(
        health_endpoint,
        provides=HealthEndpointKey,
        component=BILLING,
    )
    api = await app.controller(BillingApi)

    assert_type(controller_provider, Provider)
    assert_type(endpoint_provider, Provider)
    assert_type(api, BillingApi)
    assert_type(await api.health(), Response)
