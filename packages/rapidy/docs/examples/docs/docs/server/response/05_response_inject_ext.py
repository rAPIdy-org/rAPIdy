from rapidy.http import get, Response

@get('/')
async def handler(
    response: Response,  # <-- current response
) -> str:
    some_answer: bool = ...
    if some_answer:
        response.set_status(200)
        return 'ok'

    response.set_status(500)
    return 'not ok'