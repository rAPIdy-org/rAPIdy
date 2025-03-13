from http import HTTPStatus
from typing import Any, Final, Tuple, Type
from typing_extensions import Annotated

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web
from rapidy._base_exceptions import RapidyHandlerException
from rapidy.endpoint_handlers.attr_extractor import (
    DefaultDefineTwiceError,
    ParameterCannotUseDefaultError,
    ParameterCannotUseDefaultFactoryError,
    SpecifyBothDefaultAndDefaultFactoryError,
)
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.typedefs import Handler

DEFAULT_VALUE: Final[str] = 'DEFAULT'


async def base_test_specify_both_default_and_default_factory(
    type_: Type[RequestParamFieldInfo],
    annotation: Any = Any,
    **type_kwargs: Any,
) -> None:
    async def handler(
        p: Annotated[annotation, type_(default_factory=lambda: 'default', **type_kwargs)] = 'default',
    ) -> web.Response:
        pass

    app = web.Application()
    with pytest.raises(SpecifyBothDefaultAndDefaultFactoryError):
        app.add_routes([web.post('/', handler)])


async def base_test_incorrect_define_default_annotated_def(
    type_: Type[RequestParamFieldInfo],
    annotation: Any = Any,
    **type_kwargs: Any,
) -> None:
    async def handler(p: Annotated[annotation, type_('default', **type_kwargs)] = 'default') -> web.Response:
        pass

    app = web.Application()
    with pytest.raises(DefaultDefineTwiceError):
        app.add_routes([web.post('/', handler)])

    with pytest.raises((TypeError, ValueError)):
        type_('default', default_factory=lambda: 'default', **type_kwargs)  # NOTE: this exc raise pydantic


async def base_test_can_default(
    aiohttp_client: AiohttpClient,
    *,
    type_: Type[RequestParamFieldInfo],
    annotation: Any = Any,
    can_default: bool = True,
    **type_kwargs: Any,
) -> None:
    app = web.Application()
    counter, paths = 0, []

    for handler, default_exc in create_all_default_handlers_type(type_, annotation, **type_kwargs):
        path = f'/{counter}'
        if not can_default:
            with pytest.raises(default_exc):
                app.add_routes([web.post(path, handler)])
        else:
            app.add_routes([web.post(path, handler)])
            paths.append(path)
            counter += 1

    for path in paths:
        client = await aiohttp_client(app)
        resp = await client.post(path)
        assert resp.status == HTTPStatus.OK


def create_all_default_handlers_type(
    type_: Type[RequestParamFieldInfo],
    annotation: Any = Any,
    default: Any = DEFAULT_VALUE,
    **type_kwargs: Any,
) -> Tuple[Tuple[Handler, Type[RapidyHandlerException]], ...]:
    async def handler_1(p: Annotated[annotation, type_(**type_kwargs)] = default) -> web.Response:
        assert p == default
        return web.Response()

    async def handler_2(p: Annotated[annotation, type_(default, **type_kwargs)]) -> web.Response:
        assert p == default
        return web.Response()

    async def handler_3(
        p: Annotated[annotation, type_(default_factory=lambda: default, **type_kwargs)],
    ) -> web.Response:
        assert p == default
        return web.Response()

    async def handler_4(p: annotation = type_(default, **type_kwargs)) -> web.Response:
        assert p == default
        return web.Response()

    async def handler_5(p: annotation = type_(default_factory=lambda: default, **type_kwargs)) -> web.Response:
        assert p == default
        return web.Response()

    return (
        (handler_1, ParameterCannotUseDefaultError),
        (handler_2, ParameterCannotUseDefaultError),
        (handler_3, ParameterCannotUseDefaultFactoryError),
        (handler_4, ParameterCannotUseDefaultError),
        (handler_5, ParameterCannotUseDefaultFactoryError),
    )
