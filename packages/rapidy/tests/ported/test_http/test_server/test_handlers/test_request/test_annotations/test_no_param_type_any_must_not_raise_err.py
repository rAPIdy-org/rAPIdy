from typing import Any
from typing_extensions import Annotated

import pytest

from rapidy import Rapidy
from rapidy.http import post


async def annotated_def_handler(attr: Annotated[Any, Any]) -> None:
    pass


async def default_def_handler(attr: Any) -> None:
    pass


@pytest.mark.parametrize(
    'handler',
    [
        pytest.param(annotated_def_handler, id='annotated-def'),
        pytest.param(default_def_handler, id='default-def'),
    ],
)
def test_type_any_must_not_raise_err(handler: Any) -> None:
    Rapidy(http_route_handlers=[post.reg('/', handler)])
