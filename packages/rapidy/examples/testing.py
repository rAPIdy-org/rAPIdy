# ruff: noqa: PLR2004, S101 -- this module is an executable pytest example.

from __future__ import annotations

from rapidy import Rapidy
from rapidy.http import get
from rapidy.testing import TestClient


@get('/health')
async def health() -> dict[str, str]:
    """Return a small payload suitable for an in-process test."""
    return {'status': 'ok'}


app = Rapidy(http_route_handlers=[health])


def test_health() -> None:
    """Exercise application lifespan and HTTP without binding a socket."""
    with TestClient(app) as client:
        response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


if __name__ == '__main__':
    test_health()
