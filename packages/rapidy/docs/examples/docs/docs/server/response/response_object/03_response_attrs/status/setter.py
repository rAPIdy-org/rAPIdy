...
@get('/')
async def handler() -> ...:
    response = Response()
    response.set_status(200)
    ...

@get('/')
async def handler(response: Response) -> ...:
    response.set_status(200)
    ...