from __future__ import annotations

import base64
from typing import Any

import pytest

from rapidy import Rapidy
from rapidy.depends import FromDI
from rapidy.http import controller, get, HTTPRouter, Request, WebSocket, websocket
from rapidy.openapi import OpenAPIConfig
from rapidy.security import (
    APIKeyAuth,
    AuthBackend,
    AuthCredentials,
    BasicAuth,
    BearerAuth,
    constant_time_compare,
    SecurityConfig,
    SecurityIdentity,
    SecurityScheme,
    SimpleUser,
)
from rapidy.testing import AsyncTestClient, TestClient
from rapidy.websockets import WebSocketDisconnect

_BASIC_SECRET = 'hidden-password'


def test_api_key_runtime_openapi_identity_and_typed_di_share_one_config() -> None:
    scheme = APIKeyAuth(
        key='top-secret',
        user=SimpleUser('alice'),
        scopes=['items:read'],
    )
    security = SecurityConfig(
        schemes=[scheme],
        requirements=[{'apiKey': ['items:read']}],
    )

    @get('/items')
    async def items(
        request: Request,
        identity: FromDI[SecurityIdentity],
        credentials: FromDI[AuthCredentials],
    ) -> dict[str, Any]:
        assert identity is request.identity
        assert credentials is identity.auth
        return {
            'user': request.user.username,
            'scheme': request.auth.scheme,
            'scopes': sorted(request.auth.scopes),
        }

    app = Rapidy(
        security=security,
        openapi_config=OpenAPIConfig(title='Secured', version='1'),
        http_route_handlers=[items],
    )
    with TestClient(app) as client:
        denied = client.get('/items')
        allowed = client.get('/items', headers={'X-API-Key': 'top-secret'})
        schema_response = client.get('/schema/openapi.json')

    assert denied.status_code == 401
    assert denied.headers['www-authenticate'] == 'ApiKey realm="apiKey"'
    assert allowed.json() == {'user': 'alice', 'scheme': 'apiKey', 'scopes': ['items:read']}
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema['components']['securitySchemes']['apiKey'] == scheme.openapi_schema
    assert schema['security'] == [{'apiKey': ['items:read']}]


def test_scopes_return_403_and_route_requirements_support_or_and_and() -> None:
    primary = APIKeyAuth(name='primary', parameter_name='X-Primary', key='one', scopes=['read'])
    secondary = APIKeyAuth(name='secondary', parameter_name='X-Secondary', key='two', scopes=['write'])

    async def verify_bearer(token: str) -> SimpleUser | None:
        return SimpleUser('bearer-user') if token == 'valid-token' else None

    bearer = BearerAuth(verify_bearer)
    security = SecurityConfig(schemes=[primary, secondary, bearer])

    @get('/write', security=[{'primary': ['write']}])
    async def write() -> str:
        return 'write'

    @get('/either', security=[{'primary': []}, {'bearerAuth': []}])
    async def either(request: Request) -> str:
        return request.auth.scheme or ''

    @get('/both', security=[{'primary': [], 'secondary': []}])
    async def both(request: Request) -> list[str]:
        return list(request.auth.schemes)

    app = Rapidy(security=security, http_route_handlers=[write, either, both])
    with TestClient(app) as client:
        forbidden = client.get('/write', headers={'X-Primary': 'one'})
        bearer_response = client.get('/either', headers={'Authorization': 'Bearer valid-token'})
        missing_second = client.get('/both', headers={'X-Primary': 'one'})
        both_response = client.get('/both', headers={'X-Primary': 'one', 'X-Secondary': 'two'})

    assert forbidden.status_code == 403
    assert bearer_response.text == 'bearerAuth'
    assert missing_second.status_code == 401
    assert both_response.json() == ['primary', 'secondary']


def test_basic_auth_optional_identity_and_secret_redaction() -> None:
    scheme = BasicAuth(username='dan', password=_BASIC_SECRET, scopes=['profile'])
    bearer = BearerAuth(lambda token: SimpleUser('token-user') if token == 'token-secret' else None)

    @get('/basic', security=[{'basicAuth': []}])
    async def basic(request: Request) -> str:
        return request.user.username

    @get('/optional', security=[{}, {'bearerAuth': []}])
    async def optional(request: Request) -> bool:
        return request.identity.is_authenticated

    app = Rapidy(
        security=SecurityConfig(schemes=[scheme, bearer]),
        http_route_handlers=[basic, optional],
    )
    authorization = base64.b64encode(b'dan:hidden-password').decode()
    with TestClient(app) as client:
        authenticated = client.get('/basic', headers={'Authorization': f'Basic {authorization}'})
        anonymous = client.get('/optional')
        bearer_authenticated = client.get('/optional', headers={'Authorization': 'Bearer token-secret'})
        invalid_optional = client.get('/optional', headers={'Authorization': 'Bearer wrong'})

    assert authenticated.text == 'dan'
    assert anonymous.json() is False
    assert bearer_authenticated.json() is True
    assert invalid_optional.status_code == 401
    rendered = f'{scheme!r} {scheme.backend!r} {bearer!r} {bearer.backend!r}'
    assert 'hidden-password' not in rendered
    assert 'token-secret' not in rendered


def test_controller_guards_are_cumulative_and_public_clears_inherited_policy() -> None:
    events: list[str] = []

    def app_guard(_request: Request) -> None:
        events.append('app')

    async def controller_guard(_request: Request) -> None:
        events.append('controller')

    def route_guard(_request: Request) -> bool:
        events.append('route')
        return True

    @controller('/admin', security=[{'apiKey': []}], guards=[controller_guard])  # type: ignore[arg-type]
    class AdminController:
        @get('/private', guards=[route_guard])
        async def private(self) -> str:
            return 'private'

        @get('/health', public=True)
        async def health(self, request: Request) -> bool:
            return request.identity.is_authenticated

    app = Rapidy(
        security=SecurityConfig(
            schemes=[APIKeyAuth(key='secret')],
            guards=[app_guard],
        ),
        openapi_config=OpenAPIConfig(),
        http_route_handlers=[AdminController],
    )
    with TestClient(app) as client:
        denied = client.get('/admin/private')
        allowed = client.get('/admin/private', headers={'X-API-Key': 'secret'})
        public_response = client.get('/admin/health')

    assert denied.status_code == 401
    assert allowed.text == 'private'
    assert public_response.json() is False
    assert events == ['app', 'controller', 'route']
    schema = app.openapi_schema
    assert schema is not None
    assert schema['paths']['/admin/private']['get']['security'] == [{'apiKey': []}]
    assert schema['paths']['/admin/health']['get']['security'] == []


def test_router_inherits_parent_security_and_can_override_it_in_openapi() -> None:
    @get('/inherited')
    async def inherited(request: Request) -> str:
        return request.auth.scheme or ''

    @get('/overridden')
    async def overridden(request: Request) -> str:
        return request.auth.scheme or ''

    inherited_router = HTTPRouter('/v1', [inherited])
    overridden_router = HTTPRouter(
        '/v2',
        [overridden],
        security=SecurityConfig(
            schemes=[APIKeyAuth(name='childKey', parameter_name='X-Child-Key', key='child')],
            requirements=[{'childKey': []}],
        ),
    )
    app = Rapidy(
        security=SecurityConfig(
            schemes=[APIKeyAuth(name='rootKey', parameter_name='X-Root-Key', key='root')],
            requirements=[{'rootKey': []}],
        ),
        openapi_config=OpenAPIConfig(),
        http_route_handlers=[inherited_router, overridden_router],
    )
    with TestClient(app) as client:
        inherited_response = client.get('/v1/inherited', headers={'X-Root-Key': 'root'})
        wrong_parent = client.get('/v2/overridden', headers={'X-Root-Key': 'root'})
        child_response = client.get('/v2/overridden', headers={'X-Child-Key': 'child'})

    assert inherited_response.text == 'rootKey'
    assert wrong_parent.status_code == 401
    assert child_response.text == 'childKey'
    schema = app.openapi_schema
    assert schema is not None
    assert schema['security'] == [{'rootKey': []}]
    assert 'security' not in schema['paths']['/v1/inherited']['get']
    assert schema['paths']['/v2/overridden']['get']['security'] == [{'childKey': []}]
    assert set(schema['components']['securitySchemes']) >= {'rootKey', 'childKey'}


@pytest.mark.asyncio
async def test_websocket_uses_same_security_identity_and_rejects_with_policy_code() -> None:
    @websocket('/ws', security=[{'apiKey': ['chat']}])
    async def secured_socket(
        socket: WebSocket,
        request: Request,
        identity: FromDI[SecurityIdentity],
    ) -> None:
        assert identity is request.identity
        assert socket.identity is request.identity
        await socket.accept()
        await socket.send_json({'user': socket.user.username, 'scopes': sorted(socket.auth.scopes)})

    app = Rapidy(
        security=SecurityConfig(
            schemes=[APIKeyAuth(key='ws-secret', user=SimpleUser('ws-user'), scopes=['chat'])],
        ),
        http_route_handlers=[secured_socket],
    )
    async with AsyncTestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as denied:
            async with client.websocket_connect('/ws'):
                pass
        async with client.websocket_connect('/ws', headers={'X-API-Key': 'ws-secret'}) as session:
            payload = await session.receive_json()

    assert denied.value.code == 1008
    assert denied.value.reason == 'Unauthorized'
    assert payload == {'user': 'ws-user', 'scopes': ['chat']}


def test_security_config_rejects_unknown_and_conflicting_openapi_contracts() -> None:
    with pytest.raises(ValueError, match='Unknown security schemes'):
        SecurityConfig(requirements=[{'missing': []}])

    security = SecurityConfig(
        schemes=[APIKeyAuth(key='secret')],
        requirements=[{'apiKey': []}],
    )
    with pytest.raises(ValueError, match='conflicts'):
        Rapidy(
            security=security,
            openapi_config=OpenAPIConfig(security=[{}]),
        )

    with pytest.raises(ValueError, match='Conflicting OpenAPI security scheme'):
        Rapidy(
            security=security,
            openapi_config=OpenAPIConfig(
                security_schemes={'apiKey': {'type': 'apiKey', 'name': 'Other', 'in': 'header'}},
            ),
        )


def test_custom_backend_api_key_locations_and_guard_false() -> None:
    class CustomBackend(AuthBackend):
        async def authenticate(self, request: Request) -> SecurityIdentity | None:
            if request.headers.get('X-Custom') is None:
                return None
            return SecurityIdentity(
                user=SimpleUser('custom'),
                auth=AuthCredentials(scopes=frozenset({'custom'}), schemes=('custom',)),
            )

    query = APIKeyAuth(name='queryKey', parameter_name='access_key', location='query', key='query-secret')
    cookie = APIKeyAuth(name='cookieKey', parameter_name='session_key', location='cookie', key='cookie-secret')
    custom = SecurityScheme(
        'custom',
        CustomBackend(),
        {'type': 'apiKey', 'name': 'X-Custom', 'in': 'header'},
        challenge='Custom',
    )

    @get('/query', security=[{'queryKey': []}])
    async def query_route(request: Request) -> str:
        return request.auth.scheme or ''

    @get('/cookie', security=[{'cookieKey': []}])
    async def cookie_route(request: Request) -> str:
        return request.auth.scheme or ''

    @get('/custom', security=[{'custom': ['custom']}])
    async def custom_route(request: Request) -> str:
        return request.user.username

    @get('/guarded', guards=[lambda _request: False])
    async def guarded() -> str:
        return 'unreachable'

    app = Rapidy(
        security=SecurityConfig(schemes=[query, cookie, custom]),
        http_route_handlers=[query_route, cookie_route, custom_route, guarded],
    )
    with TestClient(app) as client:
        query_response = client.get('/query?access_key=query-secret')
        cookie_response = client.get('/cookie', cookies={'session_key': 'cookie-secret'})
        custom_response = client.get('/custom', headers={'X-Custom': 'yes'})
        rejected = client.get('/guarded')
        invalid = client.get('/query?access_key=wrong')

    assert query_response.text == 'queryKey'
    assert cookie_response.text == 'cookieKey'
    assert custom_response.text == 'custom'
    assert rejected.status_code == 403
    assert invalid.status_code == 401


def test_security_primitives_validate_configuration_and_compare_bytes() -> None:
    assert constant_time_compare('same', b'same')
    assert not constant_time_compare('left', 'right')

    with pytest.raises(ValueError, match='location'):
        APIKeyAuth(key='secret', location='body')
    with pytest.raises(ValueError, match='exactly one'):
        APIKeyAuth()
    with pytest.raises(ValueError, match='exactly one'):
        APIKeyAuth(key='secret', verify=lambda _key: None)
    with pytest.raises(ValueError, match='must not be empty'):
        APIKeyAuth(key='')
    with pytest.raises(ValueError, match='either'):
        BasicAuth()
    with pytest.raises(ValueError, match='both'):
        BasicAuth(username='only')
    with pytest.raises(ValueError, match='quotes'):
        BasicAuth(username='user', password=_BASIC_SECRET, realm='bad"realm')
    with pytest.raises(ValueError, match='may contain'):
        SecurityScheme('bad name', APIKeyAuth(key='nested'), {'type': 'http', 'scheme': 'bearer'})
    with pytest.raises(TypeError, match='guards'):
        SecurityConfig(guards=[None])  # type: ignore[list-item]
