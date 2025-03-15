from typing import Any

import pytest

from rapidy import web
from rapidy.endpoint_handlers.http.request.data_validators import AttributeAlreadyExistsError
from rapidy.parameters.http import Header


async def test_already_exist() -> None:
    async def handler(
        _: Any = Header(alias='same_name'),
        __: Any = Header(alias='same_name'),
    ) -> Any:
        return web.Response()

    app = web.Application()
    with pytest.raises(AttributeAlreadyExistsError):
        app.add_routes([web.post('/', handler)])
