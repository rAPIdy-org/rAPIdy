# Аутентификация и авторизация

`SecurityConfig` служит единым источником для runtime-аутентификации и OpenAPI security metadata. Схема объединяет
`AuthBackend` с OpenAPI-описанием, а requirement использует нативную форму OpenAPI.

```python
import os

from rapidy import Rapidy
from rapidy.http import get, Request
from rapidy.openapi import OpenAPIConfig
from rapidy.security import APIKeyAuth, SecurityConfig, SimpleUser


api_key = APIKeyAuth(
    key=os.environ['ITEMS_API_KEY'],
    user=SimpleUser('items-service'),
    scopes=['items:read'],
)
security = SecurityConfig(
    schemes=[api_key],
    requirements=[{'apiKey': ['items:read']}],
)


@get('/items')
async def items(request: Request) -> dict[str, str]:
    return {'user': request.user.display_name}


@get('/health', public=True)
async def health() -> str:
    return 'ok'


app = Rapidy(
    security=security,
    openapi_config=OpenAPIConfig(title='Items API', version='1'),
    http_route_handlers=[items, health],
)
```

Отсутствующие или неверные credentials возвращают HTTP 401 и `WWW-Authenticate`, если схема задаёт challenge.
Аутентифицированный пользователь без требуемых scopes получает HTTP 403. JSON OpenAPI и UI публичны по умолчанию,
поэтому глобальная policy не закрывает клиентам описание способа входа. `OpenAPIConfig(public=False)` заставляет
schema/UI наследовать ту же runtime policy.

## Requirements и наследование

Requirements следуют семантике OpenAPI:

- отдельные mapping — альтернативы (OR): `security=[{'apiKey': []}, {'bearerAuth': []}]`;
- несколько схем в одном mapping обязательны одновременно (AND): `security=[{'first': [], 'second': []}]`;
- должны присутствовать все scopes: `security=[{'bearerAuth': ['items:write']}]`;
- пустой mapping добавляет анонимную альтернативу: `security=[{}, {'bearerAuth': []}]`;
- `security=[]` снимает аутентификацию с route, но сохраняет унаследованные guards;
- `public=True` явно снимает и аутентификацию, и guards.

Policy приложения наследуется `HTTPRouter`. Router с собственным `SecurityConfig` переопределяет default requirement,
но сохраняет родительские схемы и cumulative guards. Guards controller и handler добавляются в порядке
application → router → controller → handler.

```python
from rapidy.exceptions import HTTPForbidden


def staff_only(request: Request) -> None:
    if 'staff' not in request.auth.scopes:
        raise HTTPForbidden


@get('/admin', guards=[staff_only])
async def admin() -> str:
    return 'ok'
```

Guard может быть синхронным или асинхронным. Обычно он выбрасывает HTTP exception; `False` — сокращение для HTTP 403.

## Встроенные схемы

- `APIKeyAuth` читает header, query parameter или cookie. Статический `key=` сравнивается за постоянное время;
  `verify=` передаёт проверку синхронному или асинхронному коду приложения.
- `BasicAuth` принимает verifier либо статическую пару username/password. Статические значения сравниваются за
  постоянное время.
- `BearerAuth` извлекает opaque Bearer token и передаёт проверку приложению.

Базовый package намеренно не зависит от JWT, JWK, OIDC, password hashing или cryptography. Подключите нужную
библиотеку внутри Bearer verifier либо реализуйте `AuthBackend` и свяжите его через `SecurityScheme`. Если scopes
динамические, verifier возвращает `SecurityIdentity`; любой другой non-`None` объект получает статические scopes
встроенной схемы.

Raw passwords, API keys и Bearer tokens не попадают в `AuthCredentials`. `repr` встроенных схем и backends не
показывает secrets. За безопасные логи и хранение внутри application verifier отвечает приложение.
Повторяющиеся `Authorization` и header/query API-key параметры отклоняются с HTTP 401 независимо от порядка
значений, поэтому аутентификация не может разойтись с извлечением параметров handler-а.

`Response.set_cookie()` по умолчанию выставляет `SameSite=Lax`. Для authentication cookies явно задавайте
`secure=True` и `httponly=True` (а также выбирайте `lax` или `strict` под сценарий приложения): framework не может
безопасно вывести эти флаги для произвольных cookies и локальной HTTP-разработки.

## Request, WebSocket и DI

HTTP handlers получают `request.user`, `request.auth` и `request.identity`. В WebSocket те же значения доступны и
из synthetic `Request`, и из `WebSocket`; отклонённый handshake закрывается WebSocket code 1008.

HTTP middleware не выполняются для WebSocket-соединений: `CORSMiddleware`, `TrustedHostMiddleware`, proxy/header,
redirect, compression и request-ID относятся только к HTTP. Проверки Host/Origin handshake настраиваются явно через
`WebSocketSecurityConfig`; для дополнительной WebSocket-авторизации остаются guards приложения/router/route.

```python
from rapidy.security import APIKeyAuth, SecurityConfig, WebSocketSecurityConfig


session_cookie = APIKeyAuth(
    name='sessionCookie',
    parameter_name='session',
    location='cookie',
    verify=verify_session,
)
security = SecurityConfig(
    schemes=[session_cookie],
    websocket=WebSocketSecurityConfig(
        allowed_hosts=('api.example.com',),
        allowed_origins=('https://app.example.com',),
    ),
)
```

Host patterns используют ту же семантику exact/`*.example.com`, что и `TrustedHostMiddleware`; порт при сравнении
игнорируется. Origins — точные serialized origins. Если соответствующая проверка включена, отсутствующие, битые или
повторяющиеся Host/Origin отклоняются. `allow_missing_origin=True` предназначен для non-browser clients, а `*` явно
разрешает любой валидный origin. Эти ослабления не считаются защитой route с cookie API-key scheme: для
cookie-authenticated WebSocket требуется явный список без `null`/wildcard и обязательный Origin header, что закрывает
Cross-Site WebSocket Hijacking (CSWSH).

```python
from rapidy.depends import FromDI
from rapidy.security import AuthCredentials, SecurityIdentity


@get('/me')
async def me(
    identity: FromDI[SecurityIdentity],
    credentials: FromDI[AuthCredentials],
) -> dict[str, object]:
    return {
        'user': identity.user.display_name,
        'scopes': sorted(credentials.scopes),
    }
```

На public и optional requests identity остаётся анонимной. DI разрешает её после runtime-аутентификации; raw
credential никогда не становится значением контейнера.
