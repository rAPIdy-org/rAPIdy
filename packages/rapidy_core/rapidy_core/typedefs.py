from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, Final, TypeAlias

from pydantic import BaseModel
from pydantic.fields import Deprecated
from pydantic_core import PydanticUndefined, PydanticUndefinedType

__all__ = (
    "UNSET",
    "Deprecated",
    "DictStrAny",
    "DictStrStr",
    "JSONDecoder",
    "JSONEncoder",
    "LocStr",
    "ModelOrDc",
    "NoArgAnyCallable",
    "Required",
    "ResultValidate",
    "Undefined",
    "UndefinedType",
    "Unset",
    "ValidateReturn",
    "ValidationErrorList",
)

DictStrAny: TypeAlias = dict[str, Any]
DictStrStr: TypeAlias = dict[str, str]

LocStr: TypeAlias = tuple[int | str, ...] | str
ModelOrDc: TypeAlias = type[BaseModel] | type[Any]
ResultValidate: TypeAlias = DictStrAny
ValidationErrorList: TypeAlias = list[DictStrAny]
ValidateReturn: TypeAlias = tuple[ResultValidate | None, ValidationErrorList | None]

NoArgAnyCallable: TypeAlias = Callable[[], Any]

Required = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType: TypeAlias = PydanticUndefinedType
Validator: TypeAlias = Any


class ErrorWrapper(Exception):
    """Compatibility placeholder retained from the pydantic-v2 branch of rAPIdy 1.x."""


class Unset(Enum):
    """Sentinel type used when an argument was not supplied."""

    UNSET = 0


UNSET: Final = Unset.UNSET

JSONEncoder: TypeAlias = Callable[[Any], str]
JSONDecoder: TypeAlias = Callable[[str], Any]
