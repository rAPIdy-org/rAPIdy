from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest
import rapidy_core.di as core_di

import rapidy
import rapidy.depends as rapidy_depends
import rapidy.http as rapidy_http
from rapidy import Rapidy
from rapidy.responses.streaming import StreamResponse

PARITY_DIR = Path(__file__).parent / 'parity'
DROP_INIT = frozenset(
    {
        'DataQueue',
        'EMPTY_PAYLOAD',
        'EofStream',
        'FlowControlDataQueue',
        'StreamReader',
        'GunicornUVLoopWebWorker',
        'GunicornWebWorker',
    }
)
NEW_WS_SSE = frozenset({'websocket', 'WebSocket', 'WebSocketDisconnect', 'SSEResponse'})
DROP_HTTP = frozenset(
    {
        'WebSocketResponse',
        'WebSocketReady',
        'WSMsgType',
        'static',
        'add_static',
        'FileResponse',
        'NotAppKeyWarning',
        'AppKey',
    }
)
DROP_APP_API = frozenset(
    {'router', 'add_routes', 'cleanup_ctx', 'on_response_prepare', 'startup', 'shutdown', 'cleanup'}
)


def _snapshot(name: str) -> tuple[str, ...]:
    return tuple((PARITY_DIR / name).read_text(encoding='utf-8').splitlines())


RAPIDY_HTTP_ALL = _snapshot('rapidy_1x_http_all.txt')
RAPIDY_DEPENDS_ALL = _snapshot('rapidy_1x_depends_all.txt')
RAPIDY_INIT_ALL = _snapshot('rapidy_1x_init_all.txt')


@pytest.mark.parametrize(('module', 'name'), [
    *((rapidy_http, name) for name in RAPIDY_HTTP_ALL),
    *((rapidy_depends, name) for name in RAPIDY_DEPENDS_ALL),
    *((rapidy, name) for name in RAPIDY_INIT_ALL if name not in DROP_INIT),
])
def test_reference_public_name_is_importable(module: ModuleType, name: str) -> None:
    assert getattr(module, name) is not None


def test_snapshots_and_public_all_are_exact() -> None:
    assert len(RAPIDY_HTTP_ALL) == 86
    assert len(RAPIDY_DEPENDS_ALL) == len(set(RAPIDY_DEPENDS_ALL)) == 22
    assert len(RAPIDY_INIT_ALL) == 10
    assert set(rapidy_http.__all__) == set(RAPIDY_HTTP_ALL) | NEW_WS_SSE
    assert len(rapidy_http.__all__) == len(set(rapidy_http.__all__)) == 90
    assert set(rapidy_depends.__all__) == set(RAPIDY_DEPENDS_ALL)
    assert len(rapidy_depends.__all__) == len(set(rapidy_depends.__all__)) == 22
    assert set(rapidy.__all__) == {'__version__', 'Rapidy', 'run_app'}


def test_preserved_aliases_and_framework_symbols() -> None:
    assert rapidy_http.BaseRequest is rapidy_http.Request
    assert rapidy_http.StreamResponse is StreamResponse
    assert callable(rapidy_depends.inject_http)
    assert issubclass(rapidy_depends.RapidyProvider, core_di.Provider)
    assert rapidy_depends.FromDI is core_di.FromDI
    assert all(getattr(rapidy_depends, name) is getattr(core_di, name) for name in core_di.__all__)
    assert 'inject_http' not in rapidy_depends.__all__
    assert 'RapidyProvider' not in rapidy_depends.__all__


@pytest.mark.parametrize('name', sorted(DROP_INIT))
def test_dropped_init_name_is_absent(name: str) -> None:
    with pytest.raises(AttributeError):
        getattr(rapidy, name)


@pytest.mark.parametrize('name', sorted(DROP_HTTP))
def test_dropped_http_name_is_absent(name: str) -> None:
    assert not hasattr(rapidy_http, name)


def test_dropped_depends_and_renamed_project_symbols_are_absent() -> None:
    assert not hasattr(rapidy, 'RapidApi')
    assert not hasattr(rapidy_depends, 'RapidApiProvider')
    assert not hasattr(rapidy_depends, 'CONTAINER_KEY')
    assert not hasattr(rapidy_depends, 'inject')
    assert not hasattr(rapidy_depends, 'UpgradeHeader')
    assert not hasattr(rapidy_depends, 'ConnectionHeader')
    assert not hasattr(rapidy_depends, 'AIOHTTP_VERSION_TUPLE')


@pytest.mark.parametrize('name', sorted(DROP_APP_API))
def test_dropped_application_api_is_absent(name: str) -> None:
    assert not hasattr(Rapidy(), name)


def test_ws_sse_additions_are_real_exports() -> None:
    assert rapidy_http.websocket is not None
    assert rapidy_http.WebSocket is not None
    assert rapidy_http.WebSocketDisconnect is not None
    assert rapidy_http.SSEResponse is not None
    assert 'HTTPMove' not in rapidy_http.__all__
    assert 'SSEEvent' not in rapidy_http.__all__
    assert 'View' not in rapidy_http.__all__
