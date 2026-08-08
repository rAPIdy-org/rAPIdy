from typing import Any

import pytest
from rapidy_core.parameters.http import Header

from rapidy import Rapidy
from rapidy.endpoint_handlers.http.request.data_validators import AttributeAlreadyExistsError
from rapidy.http import post, Response


async def test_already_exist() -> None:
    async def handler(
        _: Any = Header(alias='same_name'),
        __: Any = Header(alias='same_name'),
    ) -> Any:
        return Response()

    with pytest.raises(AttributeAlreadyExistsError):
        Rapidy(http_route_handlers=[post.reg('/', handler)])
