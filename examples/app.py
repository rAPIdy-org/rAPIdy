from rapidy import web


async def index() -> web.Response:
    return web.Response(text='Welcome home!')


async def my_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get('/', index)
    return app


if __name__ == '__main__':
    web_app = my_web_app()
    web.run_app(web_app)
