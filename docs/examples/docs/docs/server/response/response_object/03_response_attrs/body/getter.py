...
@get('/')
async def handler() -> ...:
    response = Response(body={'hello': 'rapidy'})
    body = response.body
    ...