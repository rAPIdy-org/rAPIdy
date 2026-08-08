from __future__ import annotations

import time
from urllib.request import urlopen

import pytest

from tests.live_server import live_server


@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
def test_live_request_finalizer_runs_after_response(runtime: str) -> None:
    with live_server(runtime, 'tests.apps.di_scope:app') as base_url:
        with urlopen(f'{base_url}/probe', timeout=5) as response:  # noqa: S310
            assert response.status == 200
            assert response.read() == b'ok'

        deadline = time.monotonic() + 5
        events = ''
        while time.monotonic() < deadline:
            with urlopen(f'{base_url}/events', timeout=5) as response:  # noqa: S310
                events = response.read().decode()
            if events.endswith('finalizer'):
                break
        assert events == 'handler,response_sent,finalizer'
