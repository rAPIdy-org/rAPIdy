from dataclasses import dataclass
from typing import Any

import pytest
from rapidy_core.enums import ContentType
from rapidy_core.parameters.http import Body

from rapidy import Rapidy
from rapidy.http import post
from tests.ported.client import AppClientFactory


@dataclass
class TestCase:
    id: str
    expected_ctype: str = ContentType.text_plain.value
    sent_ctype: str = ContentType.text_plain.value

    __test__ = False


test_cases = (
    TestCase(
        id='success',
    ),
    TestCase(
        id='success-type-any',
        sent_ctype='TEST/plain',
        expected_ctype='*/plain',
    ),
    TestCase(
        id='success-subtype-any',
        sent_ctype=ContentType.text_html.value,
        expected_ctype='text/*',
    ),
    TestCase(
        id='success-any',
        sent_ctype=ContentType.json.value,
        expected_ctype='*/*',
    ),
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
async def test_unsupported_type(app_client: AppClientFactory, test_case: TestCase) -> None:
    async def handler(_: Any = Body(content_type=test_case.expected_ctype)) -> Any:
        pass

    app = Rapidy(http_route_handlers=[post.reg('/', handler)])

    client = await app_client(app)
    resp = await client.post('/', data='test', headers={'Content-Type': test_case.sent_ctype})

    assert await resp.text() == ''
