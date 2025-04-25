from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Type, TypeVar
from typing_extensions import Annotated

from rapidy._base_exceptions import RapidyException
from rapidy.annotation_checkers import is_optional
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.fields.field_info import RapidyFieldInfo
from rapidy.typedefs import LocStr, ModelOrDc, Required, Undefined, ValidateReturn


class ModelFieldCreationError(RapidyException):
    """Exception raised for invalid arguments when creating a model field.

    Args:
        message: Optional custom error message.
        type_: The type of the field.
        format_fields: Additional fields to format the error message.
    """

    message = """
    Invalid args for model_field!
    Hint: check that `{type_info}` is a valid Pydantic field.
    """

    def __init__(self, message: str | None = None, *, type_: Type[Any], **format_fields: str) -> None:
        super().__init__(message, **format_fields, type_info=f'{type_}')


TRFieldInfo = TypeVar('TRFieldInfo', bound=RapidyFieldInfo)
TRapidyModelField = TypeVar('TRapidyModelField', bound='RapidyModelField')


@dataclass
class ABCRapidyModelField(ABC):
    """Abstract base class for model fields in the Rapidy framework.

    This class provides common functionality for handling field information such as
    default values, aliases, and validation. It must be extended by concrete field
    classes that implement the `required`, `default`, and `validate` methods.

    Attributes:
        name: The name of the field.
        field_info: The `RapidyFieldInfo` instance that contains metadata for the field.
    """

    name: str
    field_info: RapidyFieldInfo

    @cached_property
    def default_exists(self) -> bool:
        """Checks if a default value or factory exists for the field.

        Returns:
            bool: True if the field has a default or a default factory, False otherwise.
        """
        return self.field_info.default is not Undefined or self.field_info.default_factory is not None

    @cached_property
    def alias(self) -> str:
        """Returns the alias of the field, or the field name if no alias is set.

        Returns:
            str: The alias of the field, or the field name.
        """
        alias = self.field_info.alias
        return alias if alias is not None else self.name

    @cached_property
    def type_(self) -> Any:
        """Returns the type annotation for the field.

        Returns:
            Any: The type of the field.
        """
        return self.field_info.annotation

    @cached_property
    def need_validate(self) -> bool:
        """Indicates whether the field needs validation.

        Returns:
            bool: True if the field requires validation, False otherwise.
        """
        return self.field_info.need_validate

    @property
    @abstractmethod
    def required(self) -> bool:
        """Determines if the field is required.

        Returns:
            bool: True if the field is required, False otherwise.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def default(self) -> Any:
        """Gets the default value of the field.

        Returns:
            Any: The default value for the field.
        """
        raise NotImplementedError

    @abstractmethod
    def get_default(self) -> Any:
        """Gets the default value, possibly by invoking the default factory.

        Returns:
            Any: The default value for the field.
        """
        raise NotImplementedError

    @abstractmethod
    def validate(
        self,
        value: Any,
        values: Dict[str, Any],
        *,
        loc: LocStr,
        cls: ModelOrDc | None = None,
    ) -> ValidateReturn:
        """Validates the value of the field.

        Args:
            value: The value to validate.
            values: A dictionary of other field values to use during validation.
            loc: The location string, typically the field name.
            cls: Optional class or data class to validate against.

        Returns:
            ValidateReturn: The result of the validation (valid value and possible error).
        """
        raise NotImplementedError


if PYDANTIC_IS_V1:
    from pydantic import BaseConfig
    from pydantic.fields import ModelField
    from pydantic.schema import get_annotation_from_field_info

    class RapidyModelField(ModelField):
        """Rapidy-specific extension of Pydantic's ModelField.

        This class extends `ModelField` to include additional functionality for handling
        field validation and other attributes specific to the Rapidy framework.
        """

        field_info: RapidyFieldInfo

        @cached_property
        def default_exists(self) -> bool:
            """Checks if a default value or factory exists for the field.

            Returns:
                bool: True if the field has a default or a default factory, False otherwise.
            """
            return self.field_info.default is not Undefined or self.field_info.default_factory is not None

        @cached_property
        def alias(self) -> str:
            """Returns the alias of the field, or the field name if no alias is set.

            Returns:
                str: The alias of the field, or the field name.
            """
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @cached_property
        def need_validate(self) -> bool:
            """Indicates whether the field needs validation.

            Returns:
                bool: True if the field requires validation, False otherwise.
            """
            return self.field_info.need_validate

    def create_model_field(
        field_info: TRFieldInfo,
        *,
        class_: Type[TRapidyModelField] = RapidyModelField,
    ) -> TRapidyModelField:
        """Creates a Rapidy model field based on the provided field information.

        Args:
            field_info: The field information (`RapidyFieldInfo`).
            class_: The class to use for the field, defaulting to `RapidyModelField`.

        Returns:
            TRapidyModelField: The created model field.

        Raises:
            ModelFieldCreationError: If an error occurs during model field creation.
        """
        not_default = field_info.default in (Required, Undefined) and field_info.default_factory is None
        required = not_default and not is_optional(field_info.annotation)

        inner_annotation = get_annotation_from_field_info(
            annotation=field_info.annotation,
            field_info=field_info,
            field_name=field_info.name,
        )

        try:
            return class_(
                name=field_info.name,
                field_info=field_info,
                type_=inner_annotation,
                required=required,
                alias=field_info.alias or field_info.name,
                default=field_info.default,
                default_factory=field_info.default_factory,
                class_validators=None,
                model_config=BaseConfig,
            )
        except Exception as exc:
            raise ModelFieldCreationError(type_=field_info.annotation) from exc

    def create_model_field_by_annotation(annotation: Any) -> RapidyModelField:
        """Creates a model field based on the given annotation.

        Args:
            annotation: The type annotation for the field.

        Returns:
            RapidyModelField: The created model field.

        Raises:
            ModelFieldCreationError: If an error occurs during model field creation.
        """
        try:
            return RapidyModelField(
                name='data',
                type_=annotation,
                required=True,
                class_validators=None,
                model_config=BaseConfig,
            )
        except Exception as exc:
            raise ModelFieldCreationError(type_=annotation) from exc

else:
    from pydantic import TypeAdapter, ValidationError

    from rapidy._client_errors import regenerate_error_with_loc

    @dataclass
    class RapidyModelField(ABCRapidyModelField):  # type: ignore[no-redef]
        """Rapidy-specific implementation of a model field, based on Pydantic v2.

        This class extends the abstract base class `ABCRapidyModelField` and provides
        additional methods for validation and default value handling using Pydantic v2 features.
        """

        @property
        def alias(self) -> str:
            """Returns the alias of the field, or the field name if no alias is set.

            Returns:
                str: The alias of the field, or the field name.
            """
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @property
        def required(self) -> bool:
            """Indicates whether the field is required.

            Returns:
                bool: True if the field is required, False otherwise.
            """
            return self.field_info.is_required() and not (is_optional(self.field_info.annotation))

        @property
        def default(self) -> Any:
            """Gets the default value of the field.

            Returns:
                Any: The default value for the field, or `Undefined` if not required.
            """
            if self.field_info.is_required():
                return Undefined
            return self.field_info.get_default(call_default_factory=True)

        def get_default(self) -> Any:
            """Gets the default value, possibly by invoking the default factory.

            Returns:
                Any: The default value for the field.
            """
            return self.field_info.get_default(call_default_factory=True)

        def __post_init__(self) -> None:
            """Initializes the type adapter for the field using the field's annotation."""
            self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

        def validate(
            self,
            value: Any,
            values: Dict[str, Any],  # noqa: ARG002
            *,
            loc: LocStr,
            cls: ModelOrDc | None = None,  # noqa: ARG002
        ) -> ValidateReturn:
            """Validates the field value using the type adapter.

            Args:
                value: The value to validate.
                values: Other field values for validation.
                loc: The location string (typically the field name).
                cls: Optional class or data class for validation.

            Returns:
                ValidateReturn: The validation result (valid value and possible error).
            """
            try:
                return (
                    self._type_adapter.validate_python(
                        value,
                        from_attributes=True,
                    ),
                    None,
                )
            except ValidationError as exc:
                return None, regenerate_error_with_loc(
                    errors=exc.errors(),
                    loc=loc,
                )

    def create_model_field(
        field_info: TRFieldInfo,
        *,
        class_: Type[TRapidyModelField] = RapidyModelField,
    ) -> TRapidyModelField:
        """Creates a Rapidy model field based on the provided field information.

        Args:
            field_info: The field information (`RapidyFieldInfo`).
            class_: The class to use for the field, defaulting to `RapidyModelField`.

        Returns:
            TRapidyModelField: The created model field.

        Raises:
            ModelFieldCreationError: If an error occurs during model field creation.
        """
        try:
            return class_(
                name=field_info.name,
                field_info=field_info,
            )
        except Exception as exc:
            raise ModelFieldCreationError(type_=field_info.annotation) from exc

    def create_model_field_by_annotation(annotation: Any) -> RapidyModelField:
        """Creates a model field based on the given annotation.

        Args:
            annotation: The type annotation for the field.

        Returns:
            RapidyModelField: The created model field.

        Raises:
            ModelFieldCreationError: If an error occurs during model field creation.
        """
        name = 'data'

        field_info = RapidyFieldInfo()
        field_info.annotation = annotation
        field_info.name = name

        try:
            return RapidyModelField(name=name, field_info=field_info)
        except Exception as exc:
            raise ModelFieldCreationError(type_=annotation) from exc
