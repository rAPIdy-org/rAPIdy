import pytest

from tests.ported.client import AppClientFactory
from tests.ported.test_http.test_server.test_handlers.test_request.test_param_attrs.helpers import (
    base_test,
    create_test_cases,
    TestCase,
)


@pytest.mark.parametrize(
    'test_case',
    [pytest.param(test_case, id=test_case.id) for test_case in create_test_cases(1, 0)],
)
async def test_ge_fields(
    app_client: AppClientFactory,
    test_case: TestCase,
) -> None:
    await base_test(
        app_client=app_client,
        annotation=int,
        param=test_case.param(ge=1),
        test_case=test_case,
    )
