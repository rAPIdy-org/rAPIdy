import pytest
from typing_extensions import Annotated

from rapidy import web
from rapidy.constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.request.parameters import Body

if PYDANTIC_V1:
    PydanticSchemaGenerationError = RuntimeError
elif PYDANTIC_V2:
    from pydantic import PydanticSchemaGenerationError
else:
    raise Exception


async def test_unsupported_type() -> None:
    class Data:
        pass

    async def handler(p: Annotated[Data, Body()]) -> web.Response:
        return web.Response()

    app = web.Application()

    with pytest.raises(PydanticSchemaGenerationError):
        app.add_routes([web.post('/', handler)])
