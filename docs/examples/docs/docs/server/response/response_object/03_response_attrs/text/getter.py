...
@get('/')
async def handler() -> ...:
    response = Response(text='hello rapidy')
    body = response.text
    ...