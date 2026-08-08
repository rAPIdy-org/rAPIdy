# HTTP Server

## Description
`Rapidy` allows you to create high-performance web servers in `Python` that can receive, send, and
automatically validate any incoming or outgoing information.

A simple server can be launched in just a few lines of code:

```python
from rapidy import Rapidy, run_app
from rapidy.http import get

@get('/hello')
async def hello() -> dict[str, str]:
    return {'message': 'Hello, Web-Server!'}

rapidy = Rapidy(http_route_handlers=[hello])

if __name__ == '__main__':
    run_app(rapidy, host='0.0.0.0', port=8080)
```

## Documentation Sections
- [🚀 Creating a Web Server](application)
- [🗺️ Routing and Creating HTTP Handlers](handlers)
- [️🧭 Advanced Routing (HTTPRouter)](handlers/http_router)
- [📩 Working with Requests and Data Validation](request)
- [📤 Working with Responses and Data Serialization](response)
- [🎯 Middleware](middlewares)
- [⚠️ Handling HTTP Errors](http_errors)
- [🔄 Application Lifecycle](../lifespan)

## Let's Start Developing!
This framework is designed to speed up development and simplify working with web applications.

Ready to give it a try?

Read the documentation and get started now! 🚀
