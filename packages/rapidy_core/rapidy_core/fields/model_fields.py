from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, Any, TypeVar

from pydantic import TypeAdapter, ValidationError

from rapidy_core.annotation_checkers import is_optional
from rapidy_core.client_errors import regenerate_error_with_loc
from rapidy_core.exceptions import RapidyException
from rapidy_core.fields.field_info import RapidyFieldInfo
from rapidy_core.typedefs import LocStr, ModelOrDc, Undefined, ValidateReturn

__all__ = (
    "ABCRapidyModelField",
    "ModelFieldCreationError",
    "RapidyModelField",
    "create_model_field",
    "create_model_field_by_annotation",
)


class ModelFieldCreationError(RapidyException):
    """Error raised when a pydantic type adapter cannot be built."""

    message = """
    Invalid args for model_field!
    Hint: check that `{type_info}` is a valid Pydantic field.
    """

    def __init__(
        self, message: str | None = None, *, type_: type[Any], **format_fields: str
    ) -> None:
        super().__init__(message, **format_fields, type_info=f"{type_}")


TRFieldInfo = TypeVar("TRFieldInfo", bound=RapidyFieldInfo)
TRapidyModelField = TypeVar("TRapidyModelField", bound="RapidyModelField")


@dataclass
class ABCRapidyModelField(ABC):
    """Common field metadata and validation interface."""

    name: str
    field_info: RapidyFieldInfo

    @cached_property
    def default_exists(self) -> bool:
        """Return whether a default value or factory exists."""
        return (
            self.field_info.default is not Undefined
            or self.field_info.default_factory is not None
        )

    @cached_property
    def alias(self) -> str:
        """Return the explicit alias or field name."""
        alias = self.field_info.alias
        return alias if alias is not None else self.name

    @cached_property
    def type_(self) -> Any:
        """Return the field annotation."""
        return self.field_info.annotation

    @cached_property
    def need_validate(self) -> bool:
        """Return whether validation is enabled."""
        return self.field_info.need_validate

    @property
    @abstractmethod
    def required(self) -> bool:
        """Return whether the field is required."""
        raise NotImplementedError

    @property
    @abstractmethod
    def default(self) -> Any:
        """Return the default value."""
        raise NotImplementedError

    @abstractmethod
    def get_default(self) -> Any:
        """Resolve and return the default value."""
        raise NotImplementedError

    @abstractmethod
    def validate(
        self,
        value: Any,
        values: dict[str, Any],
        *,
        loc: LocStr,
        cls: ModelOrDc | None = None,
    ) -> ValidateReturn:
        """Validate a value and return it with optional error details."""
        raise NotImplementedError


@dataclass
class RapidyModelField(ABCRapidyModelField):
    """Pydantic-v2 implementation of a rAPIdy model field."""

    @property
    def alias(self) -> str:
        """Return the explicit alias or field name."""
        alias = self.field_info.alias
        return alias if alias is not None else self.name

    @property
    def required(self) -> bool:
        """Return whether the field has neither a default nor Optional annotation."""
        return self.field_info.is_required() and not is_optional(
            self.field_info.annotation
        )

    @property
    def default(self) -> Any:
        """Return Undefined for required fields, otherwise resolve the default."""
        if self.field_info.is_required():
            return Undefined
        return self.field_info.get_default(call_default_factory=True)

    def get_default(self) -> Any:
        """Resolve and return the default value."""
        return self.field_info.get_default(call_default_factory=True)

    def __post_init__(self) -> None:
        """Build a pydantic type adapter for the field metadata."""
        self._type_adapter: TypeAdapter[Any] = TypeAdapter(
            Annotated[self.field_info.annotation, self.field_info]
        )

    def validate(
        self,
        value: Any,
        values: dict[str, Any],
        *,
        loc: LocStr,
        cls: ModelOrDc | None = None,
    ) -> ValidateReturn:
        """Validate a value, converting pydantic failures to error dictionaries."""
        try:
            return self._type_adapter.validate_python(value, from_attributes=True), None
        except ValidationError as exc:
            return None, regenerate_error_with_loc(errors=exc.errors(), loc=loc)


def create_model_field(
    field_info: TRFieldInfo,
    *,
    class_: type[TRapidyModelField] = RapidyModelField,  # type: ignore[assignment]
) -> TRapidyModelField:
    """Create a model field using a caller-provided compatible field class."""
    try:
        return class_(name=field_info.name, field_info=field_info)
    except Exception as exc:
        raise ModelFieldCreationError(type_=field_info.annotation) from exc


def create_model_field_by_annotation(annotation: Any) -> RapidyModelField:
    """Create a model field named ``data`` from an annotation."""
    name = "data"
    field_info = RapidyFieldInfo()
    field_info.annotation = annotation
    field_info.name = name

    try:
        return RapidyModelField(name=name, field_info=field_info)
    except Exception as exc:
        raise ModelFieldCreationError(type_=annotation) from exc
