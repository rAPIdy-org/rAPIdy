from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List

from rapidy.constants import DEFAULT_JSON_DECODER
from rapidy.enums import ContentType, HTTPRequestParamType
from rapidy.fields.field_info import RapidyFieldInfo
from rapidy.typedefs import Deprecated, JSONDecoder, NoArgAnyCallable, Undefined, Unset, UnsetType

__all__ = (
    'PathParam',
    'PathParams',
    'Header',
    'Headers',
    'Cookie',
    'Cookies',
    'QueryParam',
    'QueryParams',
    'Body',
)


class RequestParamFieldInfo(RapidyFieldInfo, ABC):
    """Base class for request parameter field information.

    This class is a base for fields that describe different types of request parameters.

    Attributes:
        param_type (HTTPRequestParamType): The type of the request parameter.
        extract_single (bool): Whether to extract a single value from the request parameter.
    """

    param_type: HTTPRequestParamType
    extract_single: bool = False


# BASE
class PathBase(RequestParamFieldInfo, ABC):
    """Base class for path parameters.

    This class defines the base attributes and behaviors for path parameters.

    Attributes:
        param_type (HTTPRequestParamType): Always set to HTTPRequestParamType.path.
        can_default (bool): Whether the path parameter can have a default value.
    """

    param_type = HTTPRequestParamType.path
    can_default = False


class HeaderBase(RequestParamFieldInfo, ABC):
    """Base class for header parameters.

    This class defines the base attributes and behaviors for header parameters.

    Attributes:
        param_type (HTTPRequestParamType): Always set to HTTPRequestParamType.header.
    """

    param_type = HTTPRequestParamType.header


class CookieBase(RequestParamFieldInfo, ABC):
    """Base class for cookie parameters.

    This class defines the base attributes and behaviors for cookie parameters.

    Attributes:
        param_type (HTTPRequestParamType): Always set to HTTPRequestParamType.cookie.
    """

    param_type = HTTPRequestParamType.cookie


class QueryBase(RequestParamFieldInfo, ABC):
    """Base class for query parameters.

    This class defines the base attributes and behaviors for query parameters.

    Attributes:
        param_type (HTTPRequestParamType): Always set to HTTPRequestParamType.query.
    """

    param_type = HTTPRequestParamType.query


# PARAMS
class PathParam(PathBase):
    """Class that represents a single path parameter.

    This class is designed to manage and validate a single path parameter in an HTTP request.
    It ensures that the path parameter is extracted correctly from the request URL and that it conforms
    to any validation rules defined by the user.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    extract_single = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class PathParams(PathBase):
    """Class that represents a collection of path parameters.

    This class is designed to manage and validate multiple path parameters in an HTTP request.
    It ensures that all path parameters are extracted correctly from the request URL and that they conform
    to any validation rules defined by the user.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    extract_single = False

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class Header(HeaderBase):
    """Class that represents a single HTTP header.

    This class is designed to manage and validate a single HTTP header in an HTTP request.
    It ensures that the header is extracted correctly from the request and that it conforms
    to any validation rules defined by the user.

    For correct header extraction, use the `alias` attribute to specify the name of the header
    to extract from the request.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    extract_single = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class Headers(HeaderBase):
    """Class that represents a collection of HTTP headers.

    This class is designed to manage and validate multiple HTTP headers in an HTTP request.
    It ensures that all headers are extracted correctly from the request and that they conform
    to any validation rules defined by the user.

    For correct header extraction, it is recommended to use a Pydantic model with `Field(alias=...)`
    to specify the name of each header to extract from the request.
    This approach ensures that headers are properly mapped to the fields in the Pydantic model,
    allowing for easier validation and extraction.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class Cookie(CookieBase):
    """Class that represents a single HTTP cookie.

    This class is designed to manage and validate a single cookie in an HTTP request.
    It ensures that the cookie is extracted correctly from the request and that it conforms
    to any validation rules defined by the user.

    For correct cookie extraction, use the `alias` attribute to specify the name of the cookie
    to extract from the request.
    The `alias` should be the name of the cookie as it appears in the HTTP request, ensuring proper extraction.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    extract_single = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class Cookies(CookieBase):
    """Class that represents a collection of HTTP cookies.

    This class is designed to manage and validate multiple cookies in an HTTP request.
    It ensures that all cookies are extracted correctly from the request and that they conform
    to any validation rules defined by the user.

    For correct cookie extraction, it is recommended to use a Pydantic model with `Field(alias=...)`
    to specify the name of each cookie to extract from the request.
    This approach ensures that cookies are properly mapped to the fields in the Pydantic model, making validation
    and extraction easier.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class QueryParam(QueryBase):
    """Class that represents a single query parameter in an HTTP request.

    This class is designed to manage and validate a single query parameter in an HTTP request.
    It ensures that the query parameter is extracted correctly from the request and that it conforms
    to any validation rules defined by the user.

    For correct query parameter extraction, use the `alias` attribute to specify the name of the query parameter
    to extract from the request.
    The `alias` should be the name of the query parameter as it appears in the HTTP request, ensuring proper extraction.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    extract_single = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class QueryParams(QueryBase):
    """Class that represents a collection of query parameters in an HTTP request.

    This class is designed to manage and validate multiple query parameters in an HTTP request.
    It ensures that all query parameters are extracted correctly from the request and that they conform
    to any validation rules defined by the user.

    For correct query parameter extraction, it is recommended to use a Pydantic model with `Field(alias=...)`
    to specify the name of each query parameter to extract from the request.
    This approach ensures that query parameters are properly mapped to the fields in the Pydantic model,
    simplifying both validation and extraction.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )


class Body(RequestParamFieldInfo):
    """Class that represents the body of an HTTP request.

    This class is designed to manage and validate the body content in an HTTP request.
    It ensures that the body is extracted correctly from the request and that it conforms to any validation rules
    defined by the user.

    The body is typically the main content of the request (e.g., JSON, XML, form data).
    This class handles the extraction and validation of that content.

    Args:
        default (Any, optional): The default value for the field. Defaults to Undefined.
        default_factory (Union[NoArgAnyCallable, None], optional): Callable to generate the default value.
        alias (Union[str, None], optional): Alias for the field.
        alias_priority (Union[int, None], optional): The priority of the alias.
        validation_alias (Union[str, None], optional): Alias used for validation.
        serialization_alias (Union[str, None], optional): Alias for serialization.
        title (Union[str, None], optional): The title of the field.
        description (Union[str, None], optional): The description of the field.
        gt (Union[float, None], optional): Greater-than constraint for numeric fields.
        ge (Union[float, None], optional): Greater-than-or-equal constraint.
        lt (Union[float, None], optional): Less-than constraint for numeric fields.
        le (Union[float, None], optional): Less-than-or-equal constraint.
        min_length (Union[int, None], optional): Minimum length for string fields.
        max_length (Union[int, None], optional): Maximum length for string fields.
        pattern (Union[str, None], optional): Regex pattern for string fields.
        discriminator (Union[str, None], optional): Discriminator field in case of inheritance.
        strict (Union[bool, None], optional): Flag for strict validation.
        multiple_of (Union[float, None], optional): The number must be a multiple of this value.
        allow_inf_nan (Union[bool, None], optional): Whether Inf and NaN are allowed.
        max_digits (Union[int, None], optional): Maximum number of digits for decimal fields.
        decimal_places (Union[int, None], optional): Number of decimal places for decimal fields.
        deprecated (Union[Deprecated, str, bool, None], optional): Deprecation information.
        examples (Union[List[Any], None], optional): Example values for the field.
        json_schema_extra (Union[Dict[str, Any], None], optional): Additional JSON schema information.
        validate (bool, optional): Whether to validate the field. Defaults to True.
    """

    param_type = HTTPRequestParamType.body

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        content_type: str | ContentType = ContentType.json,
        check_content_type: bool = True,
        json_decoder: JSONDecoder = DEFAULT_JSON_DECODER,
        **extra: Any,
    ) -> None:
        super().__init__(
            default,
            default_factory=default_factory,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            deprecated=deprecated,
            examples=examples,
            json_schema_extra=json_schema_extra,
            validate=validate,
            **extra,
        )

        self.content_type = content_type
        self.json_decoder = json_decoder
        self.check_content_type = check_content_type
