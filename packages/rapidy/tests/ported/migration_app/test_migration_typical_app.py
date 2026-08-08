from __future__ import annotations

from difflib import unified_diff
from pathlib import Path

from tests.ported.client import AppClientFactory
from tests.ported.migration_app.app_rapidy_2x import app

HERE = Path(__file__).parent
LAUNCH_MARKER = "if __name__ == '__main__':"


def test_migration_diff_changes_only_the_launch_block() -> None:
    source_1x = (HERE / 'app_rapidy_1x.py.txt').read_text()
    source_2x = (HERE / 'app_rapidy_2x.py').read_text()
    common_1x, marker_1x, launch_1x = source_1x.partition(LAUNCH_MARKER)
    common_2x, marker_2x, launch_2x = source_2x.partition(LAUNCH_MARKER)

    assert marker_1x == marker_2x == LAUNCH_MARKER
    assert common_1x == common_2x
    assert launch_1x != launch_2x

    changed_lines = [
        line
        for line in unified_diff(source_1x.splitlines(), source_2x.splitlines())
        if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))
    ]
    assert changed_lines
    assert not any(line[1:].lstrip().startswith(('from ', 'import ')) for line in changed_lines)


async def test_migrated_application_contract(app_client: AppClientFactory) -> None:
    client = await app_client(app)

    valid = await client.post('/items', json={'name': 'paper', 'quantity': 2})
    assert valid.status == 200
    assert await valid.json() == {'name': 'paper', 'quantity': 2}
    assert valid.headers['X-Migration'] == 'rapidy-2'

    invalid = await client.post('/items', json={'name': 'paper', 'quantity': 'many'})
    assert invalid.status == 422
    invalid_body = await invalid.json()
    assert invalid_body['errors'][0]['loc'] == ['body', 'quantity']

    routed = await client.get('/v1/users/7', headers={'X-Token': 'secret'})
    assert routed.status == 200
    assert await routed.json() == {'greeting': 'hello', 'user_id': 7, 'token': 'secret'}
    assert routed.headers['X-Migration'] == 'rapidy-2'
