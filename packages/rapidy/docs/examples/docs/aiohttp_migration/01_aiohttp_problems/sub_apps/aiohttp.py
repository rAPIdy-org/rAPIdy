from aiohttp import web

v1_app = web.Application()
app = web.Application()
app.add_subapp('/v1', v1_app)