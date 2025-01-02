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
    <a href="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml?query=branch%3Amain" target="blank">
        <img src="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml/badge.svg?branch=main?event=push" alt="license">
    </a>
    <a href="https://github.com/rAPIdy-org/rAPIdy/blob/main/LICENSE" target="blank">
        <img src="https://img.shields.io/badge/license-_MIT-%237e56c2?style=flat" alt="license">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v1.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V1">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V2">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a> -
        a fast, lightweight, and modern asynchronous web framework powered by
        <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a>
        and
        <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>.
    </i>
</p>

---

## 🚀 **Why rAPIdy?**

rAPIdy is designed for developers who need a fast, async-first web framework that combines the performance of aiohttp
with the simplicity and modern features of frameworks like FastAPI.

Simple rAPIdy server:
```python
from rapidy import Rapidy
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

app = Rapidy(http_route_handlers=[hello])
```

---

## 🔥 **Key Features**

- Fast & Lightweight – Minimal overhead, built on aiohttp
- Async-First – Fully asynchronous by design
- Built-in Validation – Uses pydantic for request validation
- Simple & Flexible – Supports both rAPIdy-style handler definitions and traditional aiohttp function-based and
class-based routing
- Middleware Support – Easily extend functionality with middleware, including built-in validation for HTTP parameters
(headers, cookies, path params, query params and body).

---

## 📦 **Installation & Setup**

Install rAPIdy via pip:
```shell
pip install rapidy
```

---

## 🏁 **First Simple Server**
```Python
{!> ./docs/index/simple_server.py !}
```

<span class="success-color">Successful</span> request validation
```bash
{!> ./docs/index/curl_correct__simple_server.sh !}
```
```text
{!> ./docs/index/curl_correct__response.txt !}
```

<span class="warning-color">Failed</span> request validation
```bash
{!> ./docs/index/curl_incorrect__simple_server.sh !}
```
```text
{!> ./docs/index/curl_incorrect__response.txt !}
```

**Quickstart Guide [Quickstart](quickstart.md)**<br/>
