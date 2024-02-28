import inspect
from abc import ABC, abstractmethod
from types import FunctionType
from typing import Any, Dict, Iterator, Set, Type

from aiohttp.web_request import Request

from rapidy._annotation_extractor import extract_handler_attr_annotations, UnknownParameterError
from rapidy._client_errors import _create_handler_info_msg, ExtractError
from rapidy._validators import validate_request_param_data
from rapidy.fields import ModelField
from rapidy.request_params import (
    create_param_model_field_by_request_param,
    RapidParamFieldInfo,
    RapidParamType,
    ValidateType,
)
from rapidy.typedefs import ValidateReturn


class AnnotationContainerAddFieldError(TypeError):
    pass


class ParamAnnotationContainer(ABC):
    def __init__(self, extractor: Any, param_type: RapidParamType) -> None:
        self.extractor = extractor
        self.param_type = param_type

    @abstractmethod
    async def get_request_data(  # noqa: WPS463
            self,
            request: Request,
    ) -> ValidateReturn:  # pragma: no cover
        pass

    @abstractmethod
    def add_field(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_default: Any,
    ) -> None:  # pragma: no cover
        pass


class ParamAnnotationContainerOnlyExtract(ParamAnnotationContainer):
    def __init__(self, extractor: Any, param_type: RapidParamType, param_name: str) -> None:
        super().__init__(extractor=extractor, param_type=param_type)
        self.param_name = param_name
        self.already_define = False
        self.param_default = None

    def add_field(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_default: Any,
    ) -> None:
        if self.already_define:
            raise AnnotationContainerAddFieldError

        self.already_define = True
        self.param_default = param_default if param_default is not inspect.Signature.empty else None

    async def get_request_data(
            self,
            request: Request,
    ) -> ValidateReturn:
        try:
            raw_data = await self.extractor(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self.param_type,))]

        if not raw_data and self.param_default:
            raw_data = self.param_default

        return {self.param_name: raw_data}, []


class ValidateParamAnnotationContainer(ParamAnnotationContainer, ABC):
    single_model: bool

    def __init__(self, extractor: Any, param_type: RapidParamType):
        super().__init__(extractor=extractor, param_type=param_type)
        self.map_model_fields_by_alias: Dict[str, ModelField] = {}

    async def get_request_data(
            self,
            request: Request,
    ) -> ValidateReturn:
        try:
            raw_data = await self.extractor(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self.param_type,))]

        return validate_request_param_data(
            required_fields_map=self.map_model_fields_by_alias,
            raw_data=raw_data,
            is_single_model=self.single_model,
        )

    def _add_field(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_default: Any,
    ) -> None:
        model_field = create_param_model_field_by_request_param(
            annotated_type=annotated_type,
            field_info=field_info,
            param_name=param_name,
            param_default=param_default,
        )
        extraction_name = model_field.alias or model_field.name
        self.map_model_fields_by_alias[extraction_name] = model_field


class ParamAnnotationContainerValidateSchema(ValidateParamAnnotationContainer):
    single_model = True

    def __init__(self, extractor: Any, param_type: RapidParamType):
        super().__init__(extractor, param_type)
        self.already_define = False

    def add_field(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_default: Any,
    ) -> None:
        if self.already_define:
            raise AnnotationContainerAddFieldError

        self._add_field(param_name, annotated_type, field_info, param_default)
        self.already_define = True


class ParamAnnotationContainerValidateParams(ValidateParamAnnotationContainer):
    single_model = False

    def __init__(self, extractor: Any, param_type: RapidParamType) -> None:
        super().__init__(extractor, param_type)
        self.added_field_info_types: Set[Type[RapidParamFieldInfo]] = set()

    def add_field(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_default: Any,
    ) -> None:
        # NOTE: Make sure that the user does not want to extract two parameters using different data extractors.
        self.added_field_info_types.add(field_info.__class__)
        if len(self.added_field_info_types) > 1:
            raise AnnotationContainerAddFieldError

        self._add_field(param_name, annotated_type, field_info, param_default)


def param_factory(
        param_name: str, validate_type: ValidateType, param_type: RapidParamType, extractor: Any,
) -> ParamAnnotationContainer:
    if validate_type.is_no_validate():
        return ParamAnnotationContainerOnlyExtract(extractor=extractor, param_type=param_type, param_name=param_name)

    if validate_type.is_schema():
        return ParamAnnotationContainerValidateSchema(extractor=extractor, param_type=param_type)

    if validate_type.is_param():
        return ParamAnnotationContainerValidateParams(extractor=extractor, param_type=param_type)

    raise  # pragma: no cover


class HandlerAnnotationContainer:
    def __init__(self) -> None:
        self._params: Dict[str, ParamAnnotationContainer] = {}

    def __iter__(self) -> Iterator[ParamAnnotationContainer]:
        for param_container in self._params.values():
            if param_container:
                yield param_container

    def add_param(
            self,
            param_name: str,
            annotated_type: Type[Any],
            field_info: RapidParamFieldInfo,
            param_type: RapidParamType,
            param_default: Any,
    ) -> None:
        param_container = self._get_or_create_param_container(
            param_type=param_type,
            param_name=param_name,
            field_info=field_info,
        )
        param_container.add_field(
            param_name=param_name,
            annotated_type=annotated_type,
            field_info=field_info,
            param_default=param_default,
        )

    def _get_or_create_param_container(
            self,
            param_type: RapidParamType,
            param_name: str,
            field_info: RapidParamFieldInfo,
    ) -> ParamAnnotationContainer:
        param_container = self._params.get(param_type)

        if not param_container:
            return self._create_param_container(param_name=param_name, param_type=param_type, field_info=field_info)

        return param_container

    def _create_param_container(
            self,
            param_name: str,
            param_type: RapidParamType,
            field_info: RapidParamFieldInfo,
    ) -> ParamAnnotationContainer:
        param_container = param_factory(
            param_name=param_name,
            validate_type=field_info.validate_type,
            extractor=field_info.extractor,
            param_type=param_type,
        )
        self._params[param_type] = param_container
        return param_container


def create_annotation_container(handler: FunctionType) -> HandlerAnnotationContainer:
    container = HandlerAnnotationContainer()

    endpoint_signature = inspect.signature(handler)
    signature_params = endpoint_signature.parameters

    for param_name, param in signature_params.items():
        try:
            attribute_type, field_info = extract_handler_attr_annotations(param=param, handler=handler)
        except UnknownParameterError:
            continue

        if isinstance(field_info, RapidParamFieldInfo):
            try:
                container.add_param(
                    annotated_type=attribute_type,
                    field_info=field_info,
                    param_name=param_name,
                    param_type=field_info.rapid_param_type,
                    param_default=param.default,
                )
            except AnnotationContainerAddFieldError:
                raise Exception(
                    'Error during attribute definition in the handler:\n'
                    '1. It is not possible to use multiple types of attribute extraction in one handler.\n'
                    '2. For a handler attribute, you cannot define two Schemas or two Raw data extractors.\n'
                    f'{_create_handler_info_msg(handler)}',
                )
        else:  # pragma: no cover
            raise

    return container
