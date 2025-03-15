from http import HTTPStatus
from typing import Any, Dict, Optional, Type
from typing_extensions import Annotated

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel

from rapidy import web
from rapidy.endpoint_handlers.attr_extractor import CannotBeOptionalError
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.version import PY_VERSION_TUPLE


async def base_test_optional(
    aiohttp_client: AiohttpClient,
    type_: Type[RequestParamFieldInfo],
    annotation: Any = Any,
    can_default: bool = True,
    **type_kwargs: Any,
) -> None:
    async def handler_annotated_def(data: Annotated[Optional[annotation], type_(**type_kwargs)]) -> web.Response:
        assert data is None
        return web.Response()

    async def handler_default_def(data: Optional[annotation] = type_(**type_kwargs)) -> web.Response:
        assert data is None
        return web.Response()

    handlers = [handler_annotated_def, handler_default_def]
    if PY_VERSION_TUPLE >= (3, 10, 0):

        async def handler_annotated_union_type_def(
            data: Annotated[annotation | None, type_(**type_kwargs)],  # type: ignore[syntax, unused-ignore]
        ) -> web.Response:
            assert data is None
            return web.Response()

        async def handler_default_union_type_def(
            data: annotation | None = type_(**type_kwargs),  # type: ignore[syntax, unused-ignore]
        ) -> web.Response:
            assert data is None
            return web.Response()

        handlers.extend((handler_annotated_union_type_def, handler_default_union_type_def))

    app = web.Application()
    counter, paths = 0, []

    for handler in handlers:
        path = f'/{counter}'
        if not can_default:
            with pytest.raises(CannotBeOptionalError):
                app.add_routes([web.post(path, handler)])  # type: ignore[arg-type]
        else:
            app.add_routes([web.post(path, handler)])  # type: ignore[arg-type]
            paths.append(path)
            counter += 1

    for path in paths:
        client = await aiohttp_client(app)
        resp = await client.post(path)
        assert resp.status == HTTPStatus.OK, (resp.status, await resp.text())


async def base_test_optional_schema_param_fields(
    aiohttp_client: AiohttpClient,
    type_: Type[RequestParamFieldInfo],
    request_kwargs: Dict[str, Any] = {},
    **type_kwargs: Any,
) -> None:
    class Schema(BaseModel):
        attr1: Optional[str] = None
        attr2: Optional[str] = None

    async def handler_annotated_def(data: Annotated[Schema, type_(**type_kwargs)]) -> web.Response:
        assert data == Schema(attr1=None, attr2=None)
        return web.Response()

    async def handler_default_def(data: Schema = type_(**type_kwargs)) -> web.Response:
        assert data == Schema(attr1=None, attr2=None)
        return web.Response()

    for handler in handler_annotated_def, handler_default_def:
        app = web.Application()
        app.add_routes([web.post('/', handler)])
        client = await aiohttp_client(app)
        resp = await client.post('/', **request_kwargs)
        assert resp.status == HTTPStatus.OK
