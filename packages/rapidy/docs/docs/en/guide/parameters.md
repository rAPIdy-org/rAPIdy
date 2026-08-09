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

## Repeated query and header values

Repeated query parameters and header fields use the declared Python type. A collection annotation such as
`list[str]`, `tuple[int, ...]`, or `set[str]` receives every physical value in wire order before Pydantic conversion.
A scalar annotation receives one value and rejects repetitions with HTTP 422 and a `duplicate_parameter` error.
The same rule applies to fields of validated `QueryParams()`/`Headers()` models and to the value annotation of a
validated mapping such as `dict[str, list[str]]`.

rAPIdy does not split comma-separated text into multiple values: `?tag=a&tag=b` is repeated input, while `?tag=a,b`
is one string. Raw plural containers declared with `validate=False` retain their native multidict behavior.

## Body formats

`Body()` expects JSON by default. It also supports text, bytes, `application/x-www-form-urlencoded`, and multipart
forms. Use `content_type` for an exact media type or a wildcard such as `application/*`; set `check_content_type=False`
only when the endpoint intentionally accepts mismatched media types.

`Request.read()`, `text()`, `json()`, and `post()` share a body cache. Ordinary bodies and URL-encoded forms use
`client_max_size`, which defaults to 1 MiB (`1024**2` bytes). Multipart parsing instead uses an independent
`MultipartLimits` policy, so an application can
accept bounded file uploads without weakening the limit for JSON or arbitrary raw bodies:

```python
from rapidy import Rapidy
from rapidy.request import MultipartLimits

app = Rapidy(
    client_max_size=1024**2,
    multipart_limits=MultipartLimits(
        max_body_size=16 * 1024**2,
        max_parts=1000,
        max_fields=1000,
        max_files=100,
        max_field_size=1024**2,
        max_file_size=8 * 1024**2,
        spool_threshold=1024**2,
    ),
)
```

Multipart input is parsed incrementally. The complete raw multipart body and uploaded files roll from memory to a
temporary file after `spool_threshold`; text fields remain in memory but are bounded by `max_field_size`. Every limit
must be a positive integer, and exceeding a limit returns HTTP 413. Calling `Request.read()` still applies
`client_max_size`, even after `post()` accepted the multipart form. Multipart files are represented by
`rapidy.request.FileField`; consumers should close files they retain. Streaming request-body injection from rAPIdy 1.x
was intentionally removed.

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
