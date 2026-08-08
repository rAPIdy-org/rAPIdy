from __future__ import annotations

from typing import Any

import pytest

from rapidy import Rapidy
from rapidy.http import Body, FileField, get, post, Request
from tests.ported.client import AppClientFactory


@pytest.mark.asyncio
async def test_app_client_http_bodies_multipart_and_lifespan(app_client: AppClientFactory) -> None:
    startup_calls = 0

    async def on_startup() -> None:
        nonlocal startup_calls
        startup_calls += 1

    @get('/ping')
    async def ping() -> dict[str, str]:
        return {'status': 'ok'}

    @post('/echo')
    async def echo(payload: dict[str, Any] = Body()) -> dict[str, Any]:
        return payload

    @post('/upload')
    async def upload(request: Request) -> dict[str, str]:
        form = await request.post()
        file = form['upload']
        assert isinstance(file, FileField)
        try:
            return {'filename': file.filename, 'content': file.file.read().decode()}
        finally:
            file.file.close()

    app = Rapidy(
        on_startup=[on_startup],
        http_route_handlers=[ping, echo, upload],
    )
    client = await app_client(app)

    assert startup_calls == 1
    ping_response = await client.get('/ping')
    assert ping_response.status == 200
    assert await ping_response.json() == {'status': 'ok'}

    echo_response = await client.post('/echo', json={'value': 1})
    assert echo_response.status == 200
    assert await echo_response.json() == {'value': 1}

    upload_response = await client.post(
        '/upload',
        files={'upload': ('hello.txt', b'hello', 'text/plain')},
    )
    assert upload_response.status == 200
    assert await upload_response.json() == {'filename': 'hello.txt', 'content': 'hello'}
