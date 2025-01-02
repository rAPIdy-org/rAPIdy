from typing import Annotated

@get('/')
async def handler(
    some_header: Annotated[str, Header(alias='Some-Header', default_factory=lambda:'SomeValue')],
) -> ...: