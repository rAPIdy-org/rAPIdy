---
hide:
  - navigation
  - toc
---

<style>
    .md-content .md-typeset h1 { display: none; }
</style>

<p align="center">
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">
        <img src="../assets/logo-teal.png" alt="rAPIdy">
    </a>
</p>

<p align="center">
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/dm/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Package downloads">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/v/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2&label=pypi%20rAPIdy" alt="Package version">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/pyversions/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Python versions">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a>
        - is a minimalist web framework for those who prioritize speed and convenience.<br/>
        Built upon <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a> and <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>,
        allowing you to fully leverage the advantages of this stack.
    </i>
</p>

---

## **Key features:**

* ✏️ Minimalism - check and retrieve data in just one line of code
* 🐍 Seamless support for Python native types
* 📔 Full integration with <a href="https://github.com/pydantic/pydantic">pydantic</a> (complete support for both **v1** and **v2**)
* 🚀 Powered by <a href="https://github.com/aio-libs/aiohttp">aiohttp</a> with support for native functionality
* 📤 Effortless extraction of basic types from incoming data in Python

## **Installation**

```bash
pip install rapidy
```

## **A simple application**

```Python
from rapidy import web
from pydantic import BaseModel, Field
from typing_extensions import Annotated

routes = web.RouteTableDef()

class BodyRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=40)

@routes.post('/api/{user_id}')
async def handler(
        request: web.Request,
        user_id: Annotated[str, web.Path],
        host: Annotated[str, web.Header(alias='Host')],
        body: Annotated[BodyRequestSchema, web.JsonBodySchema],
) -> web.Response:
    ...
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)

```
<span style="color:#008080">Success</span> request validation
```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "User", "password": "myAwesomePass"}' -v \
http://127.0.0.1:8080/api/1

< HTTP/1.1 200 OK ... {"data": "success"}
```
<span style="color:#f58080">Failed</span> request validation

```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "U", "password": "m"}' -v \
http://127.0.0.1:8080/api/1

< HTTP/1.1 422 Unprocessable Entity ...
{
    "errors": [
        {
            "loc": ["body", "username"],
            "type": "string_too_short",
            "msg": "String should have at least 3 characters",
            "ctx": {"min_length": 3}
        },
        {
            "type": "string_too_short",
            "loc": ["body", "password"],
            "msg": "String should have at least 8 characters",
            "ctx": {"min_length": 8}
        }
    ]
}

```

**<a href="quickstart">Quickstart</a>** <br/>
**<a href="examples">More examples</a>**