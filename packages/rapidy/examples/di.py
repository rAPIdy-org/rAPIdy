from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get


@dataclass(frozen=True)
class Settings:
    """Application-scoped settings."""

    service_name: str = 'users'


@dataclass(frozen=True)
class RequestId:
    """Request-scoped correlation identifier."""

    value: str


class AppProvider(Provider):
    """Provide application and request dependencies."""

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        """Return process-local application settings."""
        return Settings()

    @provide(scope=Scope.REQUEST)
    async def request_id(self) -> AsyncIterator[RequestId]:
        """Yield a unique identifier for one request."""
        yield RequestId(str(uuid4()))


@get('/context')
async def context(settings: FromDI[Settings], request_id: FromDI[RequestId]) -> dict[str, str]:
    """Return values resolved from two DI scopes."""
    return {'service': settings.service_name, 'request_id': request_id.value}


app = Rapidy(di_providers=[AppProvider()], http_route_handlers=[context])
