from typing import get_args

import pydantic_core
import rapidy_core
from rapidy_core import typedefs
from rapidy_core.typedefs import (
    UNSET,
    JSONDecoder,
    JSONEncoder,
    ModelOrDc,
    NoArgAnyCallable,
    Unset,
)


def test_unset_pair_names() -> None:
    assert rapidy_core.UNSET is not None
    assert isinstance(rapidy_core.Unset, type)
    assert rapidy_core.UNSET is rapidy_core.Unset.UNSET
    assert not hasattr(rapidy_core, "UnsetType")
    assert not hasattr(typedefs, "UnsetType")


def test_unset_singleton_identity() -> None:
    assert UNSET is Unset.UNSET


def test_unset_in_union_annotation_runtime() -> None:
    def identity(value: int | Unset = UNSET) -> object:
        return value

    assert identity() is UNSET
    assert identity(5) == 5


def test_model_or_dc_resolved() -> None:
    assert get_args(ModelOrDc)


def test_callable_aliases_importable() -> None:
    assert JSONEncoder is not None
    assert JSONDecoder is not None
    assert NoArgAnyCallable is not None


def test_no_server_or_aiohttp_aliases() -> None:
    names = (
        "Handler",
        "Middleware",
        "CallNext",
        "HandlerOrView",
        "AbstractView",
        "RouterDeco",
        "BaseHTTPRouterType",
    )
    assert all(not hasattr(typedefs, name) for name in names)


def test_pydantic_undefined_reexports() -> None:
    assert typedefs.Undefined is pydantic_core.PydanticUndefined
    assert typedefs.Deprecated is not None
