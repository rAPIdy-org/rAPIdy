from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Optional, Type, TypeVar
from typing_extensions import Annotated

from rapidy._base_exceptions import RapidyException
from rapidy.annotation_checkers import is_optional
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.fields.field_info import RapidyFieldInfo
from rapidy.typedefs import LocStr, ModelOrDc, Required, Undefined, ValidateReturn


class ModelFieldCreationError(RapidyException):
    message = """
    Invalid args for model_field!
    Hint: check that `{type_info}` is a valid Pydantic field.
    """

    def __init__(self, message: Optional[str] = None, *, type_: Type[Any], **format_fields: str) -> None:
        super().__init__(message, **format_fields, type_info=f'{type_}')


TRFieldInfo = TypeVar('TRFieldInfo', bound=RapidyFieldInfo)
TRapidyModelField = TypeVar('TRapidyModelField', bound='RapidyModelField')


@dataclass
class ABCRapidyModelField(ABC):
    name: str
    field_info: RapidyFieldInfo

    @cached_property
    def default_exists(self) -> bool:
        return self.field_info.default is not Undefined or self.field_info.default_factory is not None

    @cached_property
    def alias(self) -> str:
        alias = self.field_info.alias
        return alias if alias is not None else self.name

    @cached_property
    def type_(self) -> Any:
        return self.field_info.annotation

    @cached_property
    def need_validate(self) -> bool:
        return self.field_info.need_validate

    @property
    @abstractmethod
    def required(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def default(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_default(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def validate(
        self,
        value: Any,
        values: Dict[str, Any],
        *,
        loc: LocStr,
        cls: Optional[ModelOrDc] = None,
    ) -> ValidateReturn:
        raise NotImplementedError


if PYDANTIC_IS_V1:
    from pydantic import BaseConfig
    from pydantic.fields import ModelField
    from pydantic.schema import get_annotation_from_field_info

    class RapidyModelField(ModelField):
        field_info: RapidyFieldInfo

        @cached_property
        def default_exists(self) -> bool:
            return self.field_info.default is not Undefined or self.field_info.default_factory is not None

        @cached_property
        def alias(self) -> str:
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @cached_property
        def need_validate(self) -> bool:
            return self.field_info.need_validate

    def create_model_field(
        field_info: TRFieldInfo,
        *,
        class_: Type[TRapidyModelField] = RapidyModelField,
    ) -> TRapidyModelField:
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
        @property
        def alias(self) -> str:
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @property
        def required(self) -> bool:
            return self.field_info.is_required() and not (is_optional(self.field_info.annotation))

        @property
        def default(self) -> Any:
            if self.field_info.is_required():
                return Undefined
            return self.field_info.get_default(call_default_factory=True)

        def get_default(self) -> Any:
            return self.field_info.get_default(call_default_factory=True)

        def __post_init__(self) -> None:
            self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

        def validate(
            self,
            value: Any,
            values: Dict[str, Any],  # noqa: ARG002
            *,
            loc: LocStr,
            cls: Optional[ModelOrDc] = None,  # noqa: ARG002
        ) -> ValidateReturn:
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
        try:
            return class_(
                name=field_info.name,
                field_info=field_info,
            )
        except Exception as exc:
            raise ModelFieldCreationError(type_=field_info.annotation) from exc

    def create_model_field_by_annotation(annotation: Any) -> RapidyModelField:
        name = 'data'

        field_info = RapidyFieldInfo()
        field_info.annotation = annotation
        field_info.name = name

        try:
            return RapidyModelField(name=name, field_info=field_info)
        except Exception as exc:
            raise ModelFieldCreationError(type_=annotation) from exc
