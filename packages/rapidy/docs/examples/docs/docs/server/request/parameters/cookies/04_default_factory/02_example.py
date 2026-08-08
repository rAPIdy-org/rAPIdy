from typing import Annotated

@get('/')
async def handler(
    some_cookie: Annotated[str, Cookie(alias='Some-Cookie', default_factory=lambda:'SomeValue')],
) -> ...: