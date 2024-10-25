import inspect
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Optional, Tuple, Type, TYPE_CHECKING, Union

from aiohttp import StreamReader
from pydantic import ValidationError
from typing_extensions import Annotated

from rapidy._annotation_helpers import annotation_is_optional
from rapidy._base_exceptions import RapidyException
from rapidy._client_errors import regenerate_error_with_loc
from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy._request_param_field_info import FieldInfo, ParamFieldInfo
from rapidy.enums import HTTPRequestParamType
from rapidy.typedefs import NoArgAnyCallable, Required, Undefined, ValidateReturn

rapidy_inner_fake_annotations = {
    StreamReader,
}


class RequestModelFieldCreationError(RapidyException):
    message = """
    Invalid args for request field!
    Hint: check that `{type_info}` is a valid Pydantic field.
    """

    def __init__(self, message: Optional[str] = None, *, type_: Type[Any], **format_fields: str) -> None:
        super().__init__(message, **format_fields, type_info=f'{type_}')  # noqa: WPS221


class ResponseModelFieldCreationError(RapidyException):
    message = """
    Invalid args for response field!
    Hint: check that `{type_info}` is a valid Pydantic field (e.g. Union[Response, dict, None]).
    You can disable generating the response model from the type annotation:

    Any way of creating `aiohttp` handler paths supports disabling generating the response model.

    Examples:
        >>> InvalidPydanticType = ...  # <- obj will raise ResponseModelFieldCreationError
        >>> app = web.Application()

        >>> def handler() -> InvalidPydanticType:
        >>>     pass
        >>>
        >>> app.router.add_post('/', handler, response_validate=False)  # <- disable generating the response model

        >>> @routes.post('/', response_validate=False)  # <- disable generating the response model
        >>> def handler() -> InvalidPydanticType:
        >>>     pass

        >>> class Handler(web.View):
        >>>     def post(self) -> InvalidPydanticType:
        >>>         pass
        >>>
        >>> app.router.add_post('/', Handler, response_validate=False)  # <- disable generating the response model

        >>> route = web.post('/', Handler, response_validate=False)  # <- disable generating the response model
        >>> app.add_routes([route])
    """

    def __init__(self, message: Optional[str] = None, *, type_: Type[Any], **format_fields: str) -> None:
        super().__init__(message, **format_fields, type_info=f'{type_}')  # noqa: WPS221


@dataclass
class BaseModelField(ABC):
    name: str
    field_info: FieldInfo

    @cached_property
    def default_exists(self) -> bool:
        return self.field_info.default is not Undefined or self.field_info.default_factory is not None

    @cached_property
    def alias(self) -> str:
        alias = self.field_info.alias
        return alias if alias is not None else self.name

    @property
    @abstractmethod
    def required(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def default(self) -> Any:
        raise NotImplementedError

    def get_default(self) -> Any:
        raise NotImplementedError

    @cached_property
    def type_(self) -> Any:
        return self.field_info.annotation

    @cached_property
    def need_validate(self) -> bool:
        return self.field_info.need_validate

    def validate(
            self,
            value: Any,
            values: Dict[str, Any],
            *,
            loc: Tuple[Union[int, str], ...],
    ) -> ValidateReturn:
        raise NotImplementedError


@dataclass
class BaseRequestModelField(BaseModelField, ABC):
    http_request_param_type: HTTPRequestParamType
    field_info: ParamFieldInfo


@dataclass
class FakeRequestModelField(BaseRequestModelField):
    @property
    def required(self) -> bool:
        return True

    @property
    def default(self) -> Any:
        return Undefined

    @property
    def need_validate(self) -> bool:
        return False

    def get_default(self) -> Any:
        return Undefined


if PYDANTIC_V1:  # noqa: C901
    from pydantic import BaseConfig  # noqa: WPS433
    from pydantic.class_validators import Validator as Validator  # noqa: WPS433
    from pydantic.fields import ModelField as PydanticModelField  # noqa: WPS433
    from pydantic.schema import get_annotation_from_field_info  # noqa: WPS433

    if TYPE_CHECKING:  # pragma: no cover
        from pydantic.fields import BoolUndefined

    class ModelField(PydanticModelField):
        def __init__(
                self,
                name: str,
                type_: Type[Any],
                class_validators: Optional[Dict[str, Validator]],
                model_config: Type[BaseConfig],
                default: Any = Undefined,
                default_factory: Optional[NoArgAnyCallable] = None,
                required: 'BoolUndefined' = Undefined,
                final: bool = False,
                alias: Optional[str] = None,
                field_info: Optional[ParamFieldInfo] = None,
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
                **kw,
            )
            self.field_info: ParamFieldInfo

            field_info_default_exist = self.field_info.default is not Undefined and self.default is not ...
            self.default_exists = field_info_default_exist or self.field_info.default_factory is not None

    class RequestModelField(ModelField):
        def __init__(
                self,
                name: str,
                type_: Type[Any],
                class_validators: Optional[Dict[str, Validator]],
                model_config: Type[BaseConfig],
                default: Any = Undefined,
                default_factory: Optional[NoArgAnyCallable] = None,
                required: 'BoolUndefined' = Undefined,
                final: bool = False,
                alias: Optional[str] = None,
                field_info: Optional[ParamFieldInfo] = None,
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

            http_request_param_type: Optional[HTTPRequestParamType] = kw.pop('http_request_param_type', None)
            if http_request_param_type:
                self.http_request_param_type = http_request_param_type

        @cached_property
        def need_validate(self) -> bool:
            return self.field_info.need_validate

    def create_request_field(
            name: str,
            type_: Type[Any],
            field_info: ParamFieldInfo,
    ) -> BaseRequestModelField:
        not_default = field_info.default in (Required, Undefined) and field_info.default_factory is None
        required = not_default and not annotation_is_optional(field_info.annotation)

        kwargs: Dict[str, Any] = {
            'name': name,
            'field_info': field_info,
            'type_': type_,
            'http_request_param_type': field_info.http_request_param_type,
            'required': required,
            'alias': field_info.alias or name,
            'default': field_info.default,
            'default_factory': field_info.default_factory,
            'class_validators': {},
            'model_config': BaseConfig,
        }
        try:
            return RequestModelField(**kwargs)
        except Exception as exc:
            if field_info.annotation in rapidy_inner_fake_annotations:
                return FakeRequestModelField(
                    name=name,
                    field_info=field_info,
                    http_request_param_type=field_info.http_request_param_type,
                )
            raise RequestModelFieldCreationError(type_=type_) from exc

    def create_response_field(
            name: str,
            type_: Type[Any],
            field_info: FieldInfo,
    ) -> ModelField:
        kwargs: Dict[str, Any] = {
            'name': name,
            'field_info': field_info,
            'type_': type_,
            'required': True,
            'class_validators': {},
            'model_config': BaseConfig,
        }

        try:
            return ModelField(**kwargs)  # type: ignore[arg-type, unused-ignore]
        except Exception as exc:
            raise ResponseModelFieldCreationError(type_=type_) from exc

elif PYDANTIC_V2:
    from pydantic import TypeAdapter  # noqa: WPS433

    def get_annotation_from_field_info(
            annotation: Any,
            field_info: FieldInfo,
            field_name: str,
    ) -> Any:  # noqa: WPS440
        return annotation

    @dataclass
    class ModelField(BaseModelField):  # type: ignore[no-redef]  # noqa: WPS440
        @property
        def alias(self) -> str:
            alias = self.field_info.alias
            return alias if alias is not None else self.name

        @property
        def required(self) -> bool:
            return self.field_info.is_required() and not (annotation_is_optional(self.field_info.annotation))

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
                values: Dict[str, Any],
                *,
                loc: Tuple[Union[int, str], ...],
        ) -> ValidateReturn:
            try:
                return (
                    self._type_adapter.validate_python(
                        value,
                        from_attributes=True,
                        strict=False,  # note: it doesn't always work - pydantic err
                    ),
                    None,
                )
            except ValidationError as exc:
                return None, regenerate_error_with_loc(
                    errors=exc.errors(),
                    loc_prefix=loc,
                )

    @dataclass
    class RequestModelField(ModelField):  # type: ignore[no-redef]
        field_info: ParamFieldInfo
        http_request_param_type: HTTPRequestParamType

    def create_request_field(  # noqa: WPS440
            name: str,
            type_: Type[Any],
            field_info: ParamFieldInfo,
    ) -> BaseRequestModelField:
        try:
            return RequestModelField(  # type: ignore[call-arg]
                name=name,
                field_info=field_info,
                http_request_param_type=field_info.http_request_param_type,
            )
        except Exception as exc:
            if field_info.annotation in rapidy_inner_fake_annotations:
                return FakeRequestModelField(
                    name=name,
                    field_info=field_info,
                    http_request_param_type=field_info.http_request_param_type,
                )
            raise RequestModelFieldCreationError(type_=type_) from exc

    def create_response_field(
            name: str,
            type_: Type[Any],
            field_info: FieldInfo,
    ) -> ModelField:
        try:
            return ModelField(name=name, field_info=field_info)  # type: ignore[call-arg, unused-ignore]
        except Exception as exc:
            raise ResponseModelFieldCreationError(type_=type_) from exc

else:
    raise ValueError


def create_param_model_field(field_info: ParamFieldInfo) -> BaseRequestModelField:
    copied_field_info = deepcopy(field_info)

    copied_field_info.default = field_info.default if field_info.default is not inspect.Signature.empty else Required
    copied_field_info.default_factory = field_info.default_factory

    attribute_name = field_info.attribute_name

    inner_attribute_type = get_annotation_from_field_info(
        annotation=field_info.annotation, field_info=field_info, field_name=attribute_name,
    )

    return create_request_field(name=attribute_name, type_=inner_attribute_type, field_info=copied_field_info)


def create_response_model_field(type_: Union[Type[Any], None]) -> ModelField:
    attribute_name = 'body'

    field_info = FieldInfo(validate=True)
    field_info.set_annotation(type_)

    inner_attribute_type = get_annotation_from_field_info(
        annotation=field_info.annotation, field_info=field_info, field_name=attribute_name,
    )

    return create_response_field(name=attribute_name, type_=inner_attribute_type, field_info=field_info)
