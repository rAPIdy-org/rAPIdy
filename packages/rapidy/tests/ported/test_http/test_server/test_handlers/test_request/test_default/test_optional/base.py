from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

import pytest
from pydantic import BaseModel
from rapidy_core.parameters.http import RequestParamFieldInfo
from rapidy_core.signature import CannotBeOptionalError

from rapidy import Rapidy
from rapidy.http import post, Response
from rapidy.version import PY_VERSION_TUPLE
from tests.ported.client import AppClientFactory


async def base_test_optional(
    app_client: AppClientFactory,
    type_: type[RequestParamFieldInfo],
    annotation: Any = Any,
    can_default: bool = True,
    **type_kwargs: Any,
) -> None:
    async def handler_annotated_def(data: Annotated[annotation | None, type_(**type_kwargs)]) -> Response:
        assert data is None
        return Response()

    async def handler_default_def(data: annotation | None = type_(**type_kwargs)) -> Response:
        assert data is None
        return Response()

    handlers = [handler_annotated_def, handler_default_def]
    if PY_VERSION_TUPLE >= (3, 10, 0):

        async def handler_annotated_union_type_def(
            data: Annotated[annotation | None, type_(**type_kwargs)],  # type: ignore[syntax, unused-ignore]
        ) -> Response:
            assert data is None
            return Response()

        async def handler_default_union_type_def(
            data: annotation | None = type_(**type_kwargs),  # type: ignore[syntax, unused-ignore]
        ) -> Response:
            assert data is None
            return Response()

        handlers.extend((handler_annotated_union_type_def, handler_default_union_type_def))

    app = Rapidy()
    counter, paths = 0, []

    for handler in handlers:
        path = f'/{counter}'
        if not can_default:
            with pytest.raises(CannotBeOptionalError):
                app.add_http_router(post.reg(path, handler))  # type: ignore[arg-type]
        else:
            app.add_http_router(post.reg(path, handler))  # type: ignore[arg-type]
            paths.append(path)
            counter += 1

    for path in paths:
        client = await app_client(app)
        resp = await client.post(path)
        assert resp.status == HTTPStatus.OK, (resp.status, await resp.text())


async def base_test_optional_schema_param_fields(
    app_client: AppClientFactory,
    type_: type[RequestParamFieldInfo],
    request_kwargs: dict[str, Any] = {},
    **type_kwargs: Any,
) -> None:
    class Schema(BaseModel):
        attr1: str | None = None
        attr2: str | None = None

    async def handler_annotated_def(data: Annotated[Schema, type_(**type_kwargs)]) -> Response:
        assert data == Schema(attr1=None, attr2=None)
        return Response()

    async def handler_default_def(data: Schema = type_(**type_kwargs)) -> Response:
        assert data == Schema(attr1=None, attr2=None)
        return Response()

    for handler in handler_annotated_def, handler_default_def:
        app = Rapidy(http_route_handlers=[post.reg('/', handler)])
        client = await app_client(app)
        resp = await client.post('/', **request_kwargs)
        assert resp.status == HTTPStatus.OK
