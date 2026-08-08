from http import HTTPStatus
from typing import Any, Final, TYPE_CHECKING
from typing_extensions import Annotated

import pytest
from rapidy_core.parameters.http import RequestParamFieldInfo
from rapidy_core.signature import (
    DefaultDefineTwiceError,
    ParameterCannotUseDefaultError,
    ParameterCannotUseDefaultFactoryError,
    SpecifyBothDefaultAndDefaultFactoryError,
)

from rapidy import Rapidy
from rapidy._base_exceptions import RapidyHandlerException
from rapidy.http import post, Response
from rapidy.typedefs import Handler

if TYPE_CHECKING:
    from tests.ported.client import AppClientFactory

DEFAULT_VALUE: Final[str] = 'DEFAULT'


async def base_test_specify_both_default_and_default_factory(
    type_: type[RequestParamFieldInfo],
    annotation: Any = Any,
    **type_kwargs: Any,
) -> None:
    async def handler(
        p: Annotated[annotation, type_(default_factory=lambda: 'default', **type_kwargs)] = 'default',
    ) -> Response:
        pass

    with pytest.raises(SpecifyBothDefaultAndDefaultFactoryError):
        Rapidy(http_route_handlers=[post.reg('/', handler)])


async def base_test_incorrect_define_default_annotated_def(
    type_: type[RequestParamFieldInfo],
    annotation: Any = Any,
    **type_kwargs: Any,
) -> None:
    async def handler(p: Annotated[annotation, type_('default', **type_kwargs)] = 'default') -> Response:
        pass

    with pytest.raises(DefaultDefineTwiceError):
        Rapidy(http_route_handlers=[post.reg('/', handler)])

    with pytest.raises((TypeError, ValueError)):
        type_('default', default_factory=lambda: 'default', **type_kwargs)  # NOTE: this exc raise pydantic


async def base_test_can_default(
    app_client: 'AppClientFactory',
    *,
    type_: type[RequestParamFieldInfo],
    annotation: Any = Any,
    can_default: bool = True,
    **type_kwargs: Any,
) -> None:
    app = Rapidy()
    counter, paths = 0, []

    for handler, default_exc in create_all_default_handlers_type(type_, annotation, **type_kwargs):
        path = f'/{counter}'
        if not can_default:
            with pytest.raises(default_exc):
                app.add_http_router(post.reg(path, handler))
        else:
            app.add_http_router(post.reg(path, handler))
            paths.append(path)
            counter += 1

    for path in paths:
        client = await app_client(app)
        resp = await client.post(path)
        assert resp.status == HTTPStatus.OK


def create_all_default_handlers_type(
    type_: type[RequestParamFieldInfo],
    annotation: Any = Any,
    default: Any = DEFAULT_VALUE,
    **type_kwargs: Any,
) -> tuple[tuple[Handler, type[RapidyHandlerException]], ...]:
    async def handler_1(p: Annotated[annotation, type_(**type_kwargs)] = default) -> Response:
        assert p == default
        return Response()

    async def handler_2(p: Annotated[annotation, type_(default, **type_kwargs)]) -> Response:
        assert p == default
        return Response()

    async def handler_3(
        p: Annotated[annotation, type_(default_factory=lambda: default, **type_kwargs)],
    ) -> Response:
        assert p == default
        return Response()

    async def handler_4(p: annotation = type_(default, **type_kwargs)) -> Response:
        assert p == default
        return Response()

    async def handler_5(p: annotation = type_(default_factory=lambda: default, **type_kwargs)) -> Response:
        assert p == default
        return Response()

    return (
        (handler_1, ParameterCannotUseDefaultError),
        (handler_2, ParameterCannotUseDefaultError),
        (handler_3, ParameterCannotUseDefaultFactoryError),
        (handler_4, ParameterCannotUseDefaultError),
        (handler_5, ParameterCannotUseDefaultFactoryError),
    )
