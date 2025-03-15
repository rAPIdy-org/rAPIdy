from rapidy.http import get

@get('/')
async def handler(
        any_attr,
) -> ...:
    print(type(any_attr))
    # web.Request