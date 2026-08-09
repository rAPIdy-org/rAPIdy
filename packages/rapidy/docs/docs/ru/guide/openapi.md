# OpenAPI и интерактивная документация

rAPIdy умеет строить OpenAPI 3.1 прямо из реестра маршрутов и Pydantic-аннотаций, которые уже используются для
runtime-валидации. Функция включается явно и не добавляет маршруты в существующее приложение без настройки.

```python
from rapidy import Rapidy
from rapidy.openapi import OpenAPIConfig


app = Rapidy(
    http_route_handlers=[read_item, create_item],
    openapi_config=OpenAPIConfig(
        title='Items API',
        version='1.0.0',
        description='Публичные операции с объектами.',
    ),
)
```

После включения доступны:

| Путь | Документ |
|---|---|
| `/schema/openapi.json` | OpenAPI 3.1 JSON |
| `/schema` | Swagger UI |
| `/schema/redoc` | ReDoc |

Swagger UI и ReDoc загружают browser assets из публичных CDN. Генерация и отдача JSON-схемы не добавляет runtime-
зависимостей и не обращается к сети.

## Метаданные операции

HTTP-декораторы принимают OpenAPI-метаданные вместе с существующими настройками ответа:

```python
@post(
    '/items',
    status_code=201,
    operation_id='createItem',
    summary='Создать объект',
    description='Проверить и сохранить один объект.',
    tags=['items'],
    responses={409: {'description': 'Объект уже существует'}},
)
async def create_item(payload: ItemIn = Body()) -> ItemOut:
    ...
```

`include_in_schema=False` скрывает вызываемый HTTP-маршрут из документа. Автоматический `HEAD` не дублируется, а
явный `@head` включается. Если `description` не задан, используется docstring хендлера. Идентификаторы операций по
умолчанию детерминированы, а повтор пользовательского `operation_id` останавливает генерацию.

## Callbacks, webhooks и связи ответов

Запросы, которые провайдер инициирует сам, описываются через `callbacks` операции, webhooks уровня приложения —
через `OpenAPIConfig.webhooks`, а `response_links` связывает основной сгенерированный ответ с другой операцией:

```python
@post(
    '/subscriptions',
    operation_id='createSubscription',
    callbacks={
        'delivery': {
            '{$request.body#/callback_url}': {
                'post': {
                    'responses': {'204': {'description': 'Callback accepted'}},
                },
            },
        },
    },
    response_links={
        'subscription': {
            'operationId': 'readSubscription',
            'parameters': {'subscription_id': '$response.body#/id'},
        },
    },
)
async def create_subscription(payload: SubscriptionIn = Body()) -> SubscriptionOut:
    ...


config = OpenAPIConfig(
    title='Subscriptions API',
    version='1.0.0',
    webhooks={
        'paymentReceived': {
            'post': {
                'responses': {'204': {'description': 'Webhook accepted'}},
            },
        },
    },
)
```

Значения повторяют структуры Callback, Path Item и Link из OpenAPI 3.1, поэтому runtime expressions и `$ref`
доступны без отдельного преобразующего API фреймворка. rAPIdy проверяет внешнюю структуру и гарантирует, что каждый
`operationId` из `response_links` существует в сгенерированном документе. Для внешней ссылки или JSON Pointer
используйте `operationRef`. В явно заданных `responses` стандартное поле `links` можно записывать непосредственно в
Response Object.

## Переиспользуемые компоненты

Если несколько операций, callbacks или webhooks используют один OpenAPI-объект, объявите его через
`OpenAPIComponents`:

```python
from rapidy.openapi import OpenAPIComponents, OpenAPIConfig

components = OpenAPIComponents(
    responses={
        'NotFound': {'description': 'Item not found'},
    },
    schemas={
        'TraceId': {'type': 'string', 'format': 'uuid'},
    },
)

config = OpenAPIConfig(components=components)


@get(
    '/items/{item_id}',
    responses={404: {'$ref': '#/components/responses/NotFound'}},
)
async def read_item(item_id: int = PathParam()) -> ItemOut:
    ...
```

Контейнер предоставляет все десять секций OpenAPI 3.1 с Python-именами: `schemas`, `responses`, `parameters`,
`examples`, `request_bodies`, `headers`, `security_schemes`, `links`, `callbacks` и `path_items`. Значения сохраняют
нативную структуру OpenAPI и могут ссылаться друг на друга через `$ref`. Явные schemas объединяются со схемами,
сгенерированными из Pydantic; несовместимые определения останавливают генерацию. Прежний сокращённый параметр
`OpenAPIConfig.security_schemes` остаётся доступен и объединяется с `components.security_schemes` по тому же правилу.

## Метаданные безопасности

Переиспользуемые OpenAPI security schemes задаются в конфигурации приложения, а требования выбираются глобально
или для отдельной операции:

```python
config = OpenAPIConfig(
    title='Items API',
    version='1.0.0',
    security_schemes={
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        },
    },
    security=({'bearerAuth': ()},),
)


@get('/health', security=[])
async def health() -> str:
    return 'ok'
```

Операция без `security` наследует глобальное требование документа. `security=[]` отменяет его для публичного
маршрута, а `security=[{'oauth': ['items:write']}]` выбирает другую схему и scopes. `security=[{}]` означает, что
авторизация необязательна. Ссылка на неизвестную схему или некорректное определение останавливают генерацию вместо
создания сломанного документа.

Эти параметры только описывают API для OpenAPI-клиентов и интерфейсов документации. Они не аутентифицируют запросы
и не устанавливают runtime-политику авторизации — её нужно реализовать через зависимости или middleware rAPIdy.

## UI render plugins и offline assets

Поведение `swagger_path` и `redoc_path` по умолчанию не меняется. Явный набор UI, собственные пути и локальные assets
задаются render plugins:

```python
from rapidy.openapi import OpenAPIConfig, RedocRenderPlugin, SwaggerRenderPlugin


config = OpenAPIConfig(
    title='Internal API',
    version='2026.1',
    render_plugins=(
        SwaggerRenderPlugin(
            path='/docs',
            js_url='/assets/swagger-ui-bundle.js',
            css_url='/assets/swagger-ui.css',
            options={'displayRequestDuration': True},
        ),
        RedocRenderPlugin(
            path='/reference',
            js_url='/assets/redoc.standalone.js',
        ),
    ),
)
```

Локальные URL можно отдавать маршрутами приложения, отдельным static server или reverse proxy. rAPIdy не встраивает
крупные сторонние JavaScript/CSS bundles, поэтому новая возможность не добавляет runtime-зависимость и не увеличивает
package. Явный `render_plugins` заменяет legacy UI routes; `render_plugins=()` оставляет только JSON schema.

Другой UI подключается наследованием от `OpenAPIRenderPlugin` и реализацией `render(request, openapi_schema, *,
schema_url) -> bytes`. Plugin управляет path и media type, а rAPIdy передаёт mount-aware URL схемы.

## Что выводится автоматически

- `PathParam`, `QueryParam`, `Header` и `Cookie` становятся параметрами с alias, default, constraints, description и
  признаком обязательности.
- Plural-маркеры моделей, например `QueryParams()`, разворачиваются в отдельные параметры свойств.
- `Body()` становится `requestBody` и сохраняет настроенный content type.
- Аннотация результата или `response_type` задаёт схему ответа; status и media type берутся из настроек маршрута.
- Pydantic-модели и вложенные определения переиспользуются через `components.schemas`.
- Для валидируемых маршрутов документируется ответ rAPIdy HTTP 422 с полем `errors`.
- Маршруты mounted applications получают полный путь с префиксом в схеме корневого приложения.

Схема строится лениво и кэшируется. Регистрация нового маршрута или mount до startup инвалидирует кэш.

## Свои пути и генерация без HTTP endpoint'ов

`swagger_path=None` или `redoc_path=None` отключает соответствующий UI; `json_path` переносит JSON-схему:

```python
config = OpenAPIConfig(
    title='Internal API',
    version='2026.1',
    json_path='/openapi.json',
    swagger_path='/docs',
    redoc_path=None,
)
```

Для инструмента, которому не нужны документационные HTTP-маршруты, используйте чистый генератор:

```python
from rapidy.openapi import create_openapi_schema

schema = create_openapi_schema(app.routes, OpenAPIConfig(title='Items API', version='1.0.0'))
```

Полный исполняемый пример: [`examples/openapi.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/openapi.py).
