# Parameters and validation

rAPIdy inspects handler signatures once at route registration and extracts each value from its declared HTTP source.
Pydantic v2 performs conversion and validation before the handler runs.

| Marker | Source | Typical declaration |
|---|---|---|
| `PathParam` | Route template | `item_id: int = PathParam()` |
| `QueryParam` | Query string | `page: int = QueryParam(alias='p')` |
| `Header` | Headers | `token: str = Header(alias='X-Token')` |
| `Cookie` | Cookies | `session: str = Cookie()` |
| `Body` | Request body | `payload: Model = Body()` |

```python
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, Cookie, Header, PathParam, post, QueryParam


class UserPatch(BaseModel):
    display_name: str


@post('/users/{user_id}')
async def update_user(
    payload: UserPatch = Body(),
    user_id: int = PathParam(),
    token: str = Header(alias='X-Token'),
    page: int = QueryParam(alias='page'),
    session: str = Cookie(),
) -> dict[str, object]:
    return {'user_id': user_id, 'name': payload.display_name, 'page': page}


app = Rapidy(http_route_handlers=[update_user])
```

This example is executable as
[`examples/parameters.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/parameters.py).

## Body formats

`Body()` expects JSON by default. It also supports text, bytes, `application/x-www-form-urlencoded`, and multipart
forms. Use `content_type` for an exact media type or a wildcard such as `application/*`; set `check_content_type=False`
only when the endpoint intentionally accepts mismatched media types.

`Request.read()`, `text()`, `json()`, and `post()` share a cached body. `client_max_size` is enforced while reading,
before form parsing. Multipart files are represented by `rapidy.request.FileField` and are closed during cleanup.
Streaming request-body injection from rAPIdy 1.x was intentionally removed; read the cached request body instead.

## Validation errors

Invalid path/query/header/cookie/body data produces HTTP 422:

```json
{
  "errors": [
    {
      "type": "int_parsing",
      "loc": ["body", "age"],
      "msg": "Input should be a valid integer",
      "input": "unknown"
    }
  ]
}
```

The exact Pydantic context can include `input`, `ctx`, and `url`. Body-size failures remain HTTP 413, and malformed
deadline metadata in `x-rapidy-deadline-ms` is HTTP 400.

## Response validation

The return annotation is the response schema by default. A returned Pydantic model, dataclass, collection, or scalar
is serialized by rAPIdy. Decorators accept `response_validate`, `response_exclude_none`, `response_include`,
`response_exclude`, aliases, status, content type, headers, and cookies. Return a ready `Response` or `StreamResponse`
when you need full transport control.
