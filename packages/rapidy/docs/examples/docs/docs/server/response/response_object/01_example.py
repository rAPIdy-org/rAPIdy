from rapidy.http import get, Response

@get('/')
async def handler() -> Response:
    return Response(
        body={'hello': 'rapidy'},
        status=200,
        headers={'Some-Header': 'SomeData'},
        content_type='application/json',
    )