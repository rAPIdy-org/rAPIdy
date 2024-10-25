import pytest
from typing_extensions import Annotated

from rapidy import web
from rapidy._endpoint_model_field import RequestModelFieldCreationError
from rapidy.request_parameters import Body


async def test_unsupported_type() -> None:
    class Data:
        pass

    async def handler(p: Annotated[Data, Body()]) -> web.Response:
        return web.Response()

    app = web.Application()

    with pytest.raises(RequestModelFieldCreationError):
        app.add_routes([web.post('/', handler)])
