# OpenAPI and interactive documentation

rAPIdy can generate an OpenAPI 3.1 document directly from the route registry and the Pydantic annotations already
used for runtime validation. It is opt-in, so enabling it does not add routes to an existing application unless you
ask for them.

```python
from rapidy import Rapidy
from rapidy.openapi import OpenAPIConfig


app = Rapidy(
    http_route_handlers=[read_item, create_item],
    openapi_config=OpenAPIConfig(
        title='Items API',
        version='1.0.0',
        description='Public item operations.',
    ),
)
```

This enables:

| Path | Document |
|---|---|
| `/schema/openapi.json` | OpenAPI 3.1 JSON |
| `/schema` | Swagger UI |
| `/schema/redoc` | ReDoc |

Swagger UI and ReDoc load browser assets from public CDNs. Generating and serving the JSON schema itself adds no
runtime dependency and does not contact the network.

## Operation metadata

HTTP decorators accept OpenAPI-specific metadata alongside the existing response settings:

```python
@post(
    '/items',
    status_code=201,
    operation_id='createItem',
    summary='Create an item',
    description='Validate and store one item.',
    tags=['items'],
    responses={409: {'description': 'The item already exists'}},
)
async def create_item(payload: ItemIn = Body()) -> ItemOut:
    ...
```

Use `include_in_schema=False` for an HTTP route that must remain callable but hidden from the document. Automatic
`HEAD` routes are omitted; an explicitly declared `@head` operation is included. When `description` is absent, the
handler docstring is used. Default operation IDs are deterministic and duplicate custom IDs fail schema generation.

## Callbacks, webhooks, and response links

Describe provider-initiated requests with operation `callbacks`, document application-level `webhooks`, and connect
a generated primary response to another operation with `response_links`:

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

The values follow the OpenAPI 3.1 Callback, Path Item, and Link object shapes, so runtime expressions and `$ref`
remain available without a framework-specific translation layer. rAPIdy validates the surrounding structure and
ensures that every `operationId` used by `response_links` names an operation in the generated document. Use
`operationRef` for an external or JSON Pointer reference. Links inside explicitly supplied `responses` can also be
written directly as standard Response Object metadata.

## Security metadata

Declare reusable OpenAPI security schemes in the application config and select them globally or per operation:

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

An operation without `security` inherits the document-level requirement. `security=[]` removes that requirement for
a public operation, while `security=[{'oauth': ['items:write']}]` selects a different scheme and scopes. Use
`security=[{}]` when authentication is optional. Unknown scheme names and malformed scheme definitions fail schema
generation instead of producing a broken document.

These values describe the API to OpenAPI clients and documentation UIs only. They do not authenticate requests or
install runtime authorization policy; implement that policy with rAPIdy dependencies or middleware.

## UI render plugins and offline assets

The default `swagger_path` and `redoc_path` behavior remains unchanged. For explicit UI selection, custom paths, or
self-hosted assets, pass render plugins:

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

Local URLs may be served by application routes, an upstream static server, or a reverse proxy. rAPIdy does not vendor
the large third-party JavaScript and CSS bundles, so this adds no runtime dependency or package-size cost. Explicit
`render_plugins` replace the legacy UI routes; use `render_plugins=()` for JSON-only schema serving.

To integrate another UI, subclass `OpenAPIRenderPlugin` and implement `render(request, openapi_schema, *,
schema_url) -> bytes`. The plugin controls its path and media type, while rAPIdy supplies the mount-aware schema URL.

## What is inferred

- `PathParam`, `QueryParam`, `Header`, and `Cookie` become OpenAPI parameters with aliases, defaults, constraints,
  descriptions, and required flags.
- Plural model markers such as `QueryParams()` expand model properties into individual parameters.
- `Body()` becomes `requestBody` and preserves its configured content type.
- Return annotations or `response_type` become response schemas. Status and media type come from the route's
  response settings.
- Pydantic models and nested definitions are shared through `components.schemas`.
- Validated routes document rAPIdy's HTTP 422 `errors` response.
- Routes from mounted applications use their complete prefixed path in the root application's schema.

The schema is built lazily and cached. Registering another route or mount before startup invalidates the cache.

## Custom paths and schema-only use

Set `swagger_path=None` or `redoc_path=None` to disable either UI, and override `json_path` to move the schema:

```python
config = OpenAPIConfig(
    title='Internal API',
    version='2026.1',
    json_path='/openapi.json',
    swagger_path='/docs',
    redoc_path=None,
)
```

For tooling that does not need HTTP documentation routes, call the pure generator directly:

```python
from rapidy.openapi import create_openapi_schema

schema = create_openapi_schema(app.routes, OpenAPIConfig(title='Items API', version='1.0.0'))
```

See the complete executable [`examples/openapi.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/openapi.py).
