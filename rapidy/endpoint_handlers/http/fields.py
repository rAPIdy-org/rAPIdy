from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast, Dict

from rapidy.endpoint_handlers.http.annotation_checkers import is_stream_reader
from rapidy.enums import HTTPRequestParamType
from rapidy.fields.model_fields import ABCRapidyModelField, create_model_field, RapidyModelField
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.typedefs import LocStr, ModelOrDc, Undefined, ValidateReturn


class RequestModelField(RapidyModelField):
    """Represents a model field for a request parameter.

    Attributes:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
        http_param_type (HTTPRequestParamType): The type of the HTTP parameter.

    Args:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
    """

    field_info: RequestParamFieldInfo
    http_param_type: HTTPRequestParamType


class _RequestModelField(RapidyModelField):
    """Internal class for handling model fields in request parameters.

    Attributes:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
        http_param_type (HTTPRequestParamType): The type of the HTTP parameter.

    Args:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
    """

    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        """Returns the HTTP parameter type.

        Returns:
            HTTPRequestParamType: The type of the HTTP parameter.
        """
        return self.field_info.param_type


@dataclass
class StreamReaderModelField(ABCRapidyModelField):
    """Represents a model field for streaming data in a request.

    Attributes:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
        http_param_type (HTTPRequestParamType): The type of the HTTP parameter.
        required (bool): Indicates whether the field is required.
        default (Any): The default value for the field.
        need_validate (bool): Indicates whether the field needs validation.
        get_default (Any): Returns the default value of the field.

    Args:
        field_info (RequestParamFieldInfo): Information about the request parameter field.
    """

    field_info: RequestParamFieldInfo

    @cached_property
    def http_param_type(self) -> HTTPRequestParamType:
        """Returns the HTTP parameter type for stream reader.

        Returns:
            HTTPRequestParamType: The type of the HTTP parameter.
        """
        return self.field_info.param_type

    @cached_property
    def required(self) -> bool:
        """Indicates whether the field is required.

        Returns:
            bool: True, as stream reader fields are required.
        """
        return True

    @cached_property
    def default(self) -> Any:
        """Returns the default value for the field.

        Returns:
            Any: Undefined, as there is no default value.
        """
        return Undefined

    @cached_property
    def need_validate(self) -> bool:
        """Indicates whether the field needs validation.

        Returns:
            bool: False, as stream reader fields do not require validation.
        """
        return False

    @cached_property
    def get_default(self) -> Any:
        """Returns the default value for the field.

        Returns:
            Any: Undefined, as there is no default value.
        """
        return Undefined

    def validate(
        self,
        value: Any,
        values: Dict[str, Any],
        *,
        loc: LocStr,
        cls: ModelOrDc | None = None,
    ) -> ValidateReturn:
        """Validates the stream reader model field.

        Args:
            value (Any): The value to validate.
            values (Dict[str, Any]): The other values to consider during validation.
            loc (LocStr): The location of the value within the model.
            cls (Optional[ModelOrDc], optional): The class or data container the value belongs to.

        Raises:
            NotImplementedError: Stream reader validation is not implemented.

        Returns:
            ValidateReturn: The result of validation (not implemented).
        """
        raise NotImplementedError


def create_stream_reader_model_field(field_info: RequestParamFieldInfo) -> StreamReaderModelField:
    """Creates a StreamReaderModelField instance from the provided field information.

    Args:
        field_info (RequestParamFieldInfo): The field information to create the model field.

    Returns:
        StreamReaderModelField: A new instance of StreamReaderModelField.
    """
    return StreamReaderModelField(name=field_info.name, field_info=field_info)


def create_request_model_field(field_info: RequestParamFieldInfo) -> RequestModelField:
    """Creates a RequestModelField based on the provided field information.

    If the parameter is a stream reader, a StreamReaderModelField will be created instead.

    Args:
        field_info (RequestParamFieldInfo): The field information to create the model field.

    Returns:
        RequestModelField: A new instance of RequestModelField or StreamReaderModelField.
    """
    if field_info.param_type == HTTPRequestParamType.body and is_stream_reader(field_info.annotation):
        model_field = create_stream_reader_model_field(field_info=field_info)
    else:
        model_field = create_model_field(field_info=field_info, class_=_RequestModelField)

    return cast(RequestModelField, model_field)
