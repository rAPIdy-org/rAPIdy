from abc import ABC
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, TYPE_CHECKING, Union

from pydantic import ValidationError
from pydantic.fields import FieldInfo as FieldInfo
from typing_extensions import Annotated

from rapidy._client_errors import RequestErrorModel
from rapidy._request_params_base import ValidateType
from rapidy.constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.request_params import ParamType
from rapidy.typedefs import Required, Undefined, ValidateReturn


class Param:
    def __init__(
            self,
            param_type: ParamType,
            extractor: Any,
            validate_type: ValidateType,
            can_default: bool,
    ) -> None:
        self.param_type = param_type
        self.extractor = extractor
        self.validate_type = validate_type
        self.can_default = can_default


class ParamFieldInfo(FieldInfo, Param, ABC):
    def __init__(
            self,
            param_type: ParamType,
            extractor: Any,
            validate_type: ValidateType,
            can_default: bool = True,
            **field_info_kwargs: Any,
    ) -> None:
        FieldInfo.__init__(
            self,
            **field_info_kwargs,
        )

        Param.__init__(
            self,
            param_type=param_type,
            extractor=extractor,
            validate_type=validate_type,
            can_default=can_default,
        )


if PYDANTIC_V1:
    from pydantic import BaseConfig
    from pydantic.class_validators import Validator as Validator
    from pydantic.error_wrappers import ErrorWrapper
    from pydantic.fields import ModelField as PydanticModelField
    from pydantic.schema import get_annotation_from_field_info
    from pydantic.typing import NoArgAnyCallable as NoArgAnyCallable  # noqa: WPS113

    if TYPE_CHECKING:  # pragma: no cover
        from pydantic.fields import BoolUndefined

    class ModelField(PydanticModelField):
        def __init__(
                self,
                name: str,
                type_: Type[Any],
                class_validators: Optional[Dict[str, Validator]],
                model_config: Type[BaseConfig],
                default: Any = None,
                default_factory: Optional[NoArgAnyCallable] = None,
                required: 'BoolUndefined' = Undefined,
                final: bool = False,
                alias: Optional[str] = None,
                field_info: Optional[FieldInfo] = None,
                **kw: Any,
        ) -> None:
            super().__init__(
                name=name,
                type_=type_,
                class_validators=class_validators,
                model_config=model_config,
                default=default,
                default_factory=default_factory,
                required=required,
                final=final,
                alias=alias,
                field_info=field_info,
            )
            rapid_param_type: Optional[ParamType] = kw.pop('rapid_param_type', None)
            if rapid_param_type:
                self.rapid_param_type = rapid_param_type

    def create_field(
            name: str,
            type_: Type[Any],
            field_info: ParamFieldInfo,
    ) -> ModelField:
        kwargs: Dict[str, Any] = {
            'name': name,
            'field_info': field_info,
            'type_': type_,
            'rapid_param_type': field_info.param_type,
            'required': field_info.default in (Required, Undefined),
            'alias': field_info.alias or name,
            'default': field_info.default,
            'class_validators': {},
            'model_config': BaseConfig,
        }
        try:
            return ModelField(**kwargs)
        except Exception:
            raise Exception(
                'Invalid args for annotated request field! '
                f'Hint: check that {type_} is a valid Pydantic field type. ',
            ) from None

    def _regenerate_error_with_loc(
            *,
            errors: Sequence[Any],
            loc_prefix: Tuple[Union[str, int], ...],
    ) -> List[Dict[str, Any]]:
        return [
            {
                **err,
                'loc': loc_prefix + err.get('loc', ()),
            }
            for err in _normalize_errors(errors)
        ]

    def _normalize_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
        use_errors: List[Any] = []
        for error in errors:
            if isinstance(error, ErrorWrapper):
                new_errors = ValidationError(
                    errors=[error],
                    model=RequestErrorModel,
                ).errors()
                use_errors.extend(new_errors)
            elif isinstance(error, list):
                use_errors.extend(_normalize_errors(error))
            else:
                use_errors.append(error)
        return use_errors

elif PYDANTIC_V2:
    from dataclasses import dataclass

    from pydantic import TypeAdapter

    def get_annotation_from_field_info(annotation: Any, field_info: FieldInfo, field_name: str) -> Any:  # noqa: WPS440
        return annotation

    def _regenerate_error_with_loc(  # noqa: WPS440
            *,
            errors: Sequence[Any],
            loc_prefix: Tuple[Union[str, int], ...],
    ) -> List[Dict[str, Any]]:
        return [
            {
                **err,
                'loc': loc_prefix + err.get('loc', ()),
            }
            for err in errors
        ]

    @dataclass
    class ModelField:  # type: ignore[no-redef]  # noqa: WPS440
        name: str
        field_info: FieldInfo
        rapid_param_type: ParamType

        @property
        def alias(self) -> str:
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @property
        def required(self) -> bool:
            return self.field_info.is_required()

        @property
        def default(self) -> Any:
            if self.field_info.is_required():
                return Undefined
            return self.field_info.get_default(call_default_factory=True)

        @property
        def type_(self) -> Any:
            return self.field_info.annotation

        def __post_init__(self) -> None:
            self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

        def validate(
            self,
            value: Any,
            values: Dict[str, Any] = {},  # noqa: B006 WPS404
            *,
            loc: Tuple[Union[int, str], ...],
        ) -> ValidateReturn:
            try:
                return (
                    self._type_adapter.validate_python(value, from_attributes=True),
                    None,
                )
            except ValidationError as exc:
                return None, _regenerate_error_with_loc(
                    errors=exc.errors(),
                    loc_prefix=loc,
                )

    def create_field(  # noqa: WPS440
            name: str,
            type_: Type[Any],
            field_info: ParamFieldInfo,
    ) -> ModelField:
        field_info.annotation = type_
        return ModelField(  # type: ignore[call-arg]
            name=name,
            field_info=field_info,
            rapid_param_type=field_info.param_type,
        )
