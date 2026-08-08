from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from rapidy import Rapidy
from rapidy.exceptions import HTTPBadRequest
from rapidy.http import get, Request, Response
from tests.request_factory import make_request


@pytest.mark.parametrize(
    ('raw_value', 'expected'),
    [
        (None, None),
        (b'0', 0),
        (b'250', 250),
    ],
)
def test_deadline_valid_values(raw_value: bytes | None, expected: int | None) -> None:
    headers = () if raw_value is None else ((b'x-rapidy-deadline-ms', raw_value),)
    request, _ = make_request(headers=headers)
    assert request.deadline_remaining_ms == expected


@pytest.mark.parametrize('raw_value', [b'-1', b'1.5', b'', b' ', b'\xff'])
def test_deadline_rejects_malformed_values(raw_value: bytes) -> None:
    with pytest.raises(HTTPBadRequest):
        make_request(headers=((b'x-rapidy-deadline-ms', raw_value),))


@pytest.mark.asyncio
async def test_deadline_is_available_to_handler_and_middleware_shape() -> None:
    observed: list[int | None] = []

    @get('/deadline')
    async def deadline(request: Request) -> str:
        observed.append(request.deadline_remaining_ms)
        return str(request.deadline_remaining_ms)

    app = Rapidy(http_route_handlers=[deadline])
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.get('/deadline', headers={'x-rapidy-deadline-ms': '125'})
        malformed = await client.get('/deadline', headers={'x-rapidy-deadline-ms': '-1'})

    assert response.status_code == 200
    assert response.text == '125'
    assert malformed.status_code == 400
    assert observed == [125]

    request, _ = make_request(headers=((b'x-rapidy-deadline-ms', b'75'),))

    async def terminal(current_request: Request) -> Response:
        return Response(str(current_request.deadline_remaining_ms))

    async def middleware(current_request: Request) -> Response:
        observed.append(current_request.deadline_remaining_ms)
        return await terminal(current_request)

    middleware_response = await middleware(request)
    assert middleware_response.text == '75'
    assert observed == [125, 75]
