from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

from attrs import define
from rapidy_core.parameters.http import Body, Cookie, Header, QueryParam, RequestParamFieldInfo

from rapidy import Rapidy
from rapidy.http import post
from rapidy.typedefs import Handler
from tests.ported.client import AppClientFactory


@define(slots=True)
class TestCase:
    id: str
    param: type[RequestParamFieldInfo]
    client_kwargs: dict[str, Any]
    expected_client_err: bool = False

    __test__ = False


def create_test_cases(
    correct_value: Any,
    incorrect_value: Any | None = None,
    skip_only_str_params: bool = False,
    data_key: str = 'data',
) -> list[TestCase]:
    cases = [
        TestCase(
            id='success-body',
            param=Body,
            client_kwargs={'json': correct_value},
        ),
    ]
    if incorrect_value:
        cases.append(
            TestCase(
                id='failed-body',
                param=Body,
                client_kwargs={'json': incorrect_value},
                expected_client_err=True,
            ),
        )

    if not skip_only_str_params:
        cases.extend(
            [
                TestCase(
                    id='success-header',
                    param=Header,
                    client_kwargs={'headers': {data_key: str(correct_value)}},
                ),
                TestCase(
                    id='success-cookie',
                    param=Cookie,
                    client_kwargs={'cookies': {data_key: correct_value}},
                ),
                TestCase(
                    id='success-query-param',
                    param=QueryParam,
                    client_kwargs={'params': {data_key: correct_value}},
                ),
            ],
        )
        if incorrect_value:
            cases.extend(
                [
                    TestCase(
                        id='failed-header',
                        param=Header,
                        client_kwargs={'headers': {data_key: str(incorrect_value)}},
                        expected_client_err=True,
                    ),
                    TestCase(
                        id='failed-cookie',
                        param=Cookie,
                        client_kwargs={'cookies': {data_key: incorrect_value}},
                        expected_client_err=True,
                    ),
                    TestCase(
                        id='failed-query-param',
                        param=QueryParam,
                        client_kwargs={'params': {data_key: incorrect_value}},
                        expected_client_err=True,
                    ),
                ],
            )

    return cases


def create_handlers(annotation: Any, param: RequestParamFieldInfo) -> list[Handler]:
    async def handler1(data: Annotated[annotation, param]) -> None:
        pass

    async def handler2(data: annotation = param) -> None:
        pass

    return [handler1, handler2]


async def base_test(
    app_client: AppClientFactory,
    annotation: Any,
    param: RequestParamFieldInfo,
    test_case: TestCase,
) -> None:
    handlers = create_handlers(annotation=annotation, param=param)

    for handler in handlers:
        app = Rapidy(http_route_handlers=[post.reg('/', handler)])

        client = await app_client(app)
        resp = await client.post('/', **test_case.client_kwargs)

        if test_case.expected_client_err:
            assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
        else:
            assert resp.status == HTTPStatus.OK, await resp.text()
