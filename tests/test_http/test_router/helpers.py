from typing import Final

import pytest

PATH_1: Final[str] = '/foo1'
PATH_2: Final[str] = '/foo2'

parametrize_method_names = pytest.mark.parametrize(
    'method_name',
    ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'),
)
