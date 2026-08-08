import inspect
from typing import Annotated, Optional, Union

import rapidy_core.annotation_checkers as checkers
from rapidy_core.annotation_checkers import (
    get_base_annotations,
    is_annotated,
    is_empty,
    is_not_none_and_unset,
    is_optional,
    is_union,
    lenient_issubclass,
)
from rapidy_core.typedefs import UNSET


def test_is_union() -> None:
    assert is_union(int | str)
    assert is_union(Union[int, str])  # noqa: UP007 - exercise the legacy typing.Union spelling
    assert not is_union(int)
    assert not is_union(list[int])


def test_is_optional() -> None:
    assert is_optional(int | None)
    assert is_optional(Optional[int])  # noqa: UP045 - exercise the legacy typing.Optional spelling
    assert not is_optional(int | str)
    assert not is_optional(int)


def test_is_annotated() -> None:
    assert is_annotated(Annotated[int, "meta"])
    assert not is_annotated(int)


def test_get_base_annotations() -> None:
    assert get_base_annotations(int | str | None) == (int, str)
    assert get_base_annotations(Annotated[int, "meta"]) == (int,)
    assert get_base_annotations(str) == (str,)


def test_is_empty_and_unset_predicate() -> None:
    assert is_empty(inspect.Signature.empty)
    assert not is_empty(None)
    assert not is_empty(0)
    assert not is_not_none_and_unset(None)
    assert not is_not_none_and_unset(UNSET)
    assert is_not_none_and_unset(0)


def test_lenient_issubclass_on_classes() -> None:
    assert lenient_issubclass(bool, int)
    assert not lenient_issubclass(int, str)
    assert lenient_issubclass(int, (str, int))


def test_lenient_issubclass_on_non_class() -> None:
    assert not lenient_issubclass(42, int)
    assert not lenient_issubclass("x", str)
    assert not lenient_issubclass(None, object)


def test_lenient_issubclass_parametrized_generic() -> None:
    assert not lenient_issubclass(int, list[int])  # type: ignore[arg-type]


def test_no_version_or_private_pydantic_branch() -> None:
    source = inspect.getsource(checkers)
    assert "PY_VERSION_TUPLE" not in source
    assert "pydantic._internal" not in source
