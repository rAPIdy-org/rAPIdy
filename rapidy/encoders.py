from __future__ import annotations

import dataclasses
import datetime
import types
from collections import defaultdict, deque
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path, PurePath
from typing import Any, Callable, Deque, Dict, FrozenSet, List, overload, Pattern, Set, Tuple, Type
from typing_extensions import Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel
from pydantic.color import Color
from pydantic.networks import AnyUrl, NameEmail
from pydantic.types import SecretBytes, SecretStr

from rapidy.constants import DEFAULT_JSON_ENCODER, PYDANTIC_IS_V1
from rapidy.enums import Charset
from rapidy.typedefs import JSONEncoder

if PYDANTIC_IS_V1:
    from pydantic import AnyUrl as Url

    def pydantic_model_dump(
        model: BaseModel,
        mode: Literal['json', 'python'] = 'json',  # noqa: ARG001
        **kwargs: Any,
    ) -> Any:
        return model.dict(**kwargs)

else:
    from pydantic_core import Url

    def pydantic_model_dump(
        model: BaseModel,
        mode: Literal['json', 'python'] = 'json',
        **kwargs: Any,
    ) -> Any:
        return model.model_dump(mode=mode, **kwargs)


__all__ = (
    'jsonify',
    'Include',
    'Exclude',
    'CustomEncoder',
)

_IncludeOrExclude: TypeAlias = Set[int] | Set[str] | Dict[int, Any] | Dict[str, Any]
Include: TypeAlias = _IncludeOrExclude
Exclude: TypeAlias = _IncludeOrExclude

CustomEncoder: TypeAlias = Dict[Any, Callable[[Any], Any]]
MainSequence: TypeAlias = (
    List[Any] | Tuple[Any] | Set[Any] | FrozenSet[Any] | types.GeneratorType | Deque[Any]  # type: ignore[type-arg]
)

MainSequenceTypes: Tuple[Type[Any], ...] = (list, tuple, set, frozenset, types.GeneratorType, deque)
PassableTypes: Tuple[Type[Any], ...] = (str, int, float, type(None))


def prepare_bytes(value: bytes, charset: str) -> Any:
    return value.decode(charset)


def prepare_datetime_date(value: datetime.date | datetime.datetime | datetime.time) -> str:
    return value.isoformat()


def prepare_datetime_timedelta(value: datetime.timedelta) -> float:
    return value.total_seconds()


def prepare_decimal(value: Decimal) -> str:
    return str(value)


def prepare_enum(value: Enum) -> str:
    return value.value


def prepare_path(value: Path | PurePath) -> str:
    return str(value)


def prepare_uuid(value: UUID) -> str:
    return str(value)


def prepare_ip(value: IPv4Address | IPv4Interface | IPv4Network | IPv6Address | IPv6Interface | IPv6Network) -> str:
    return str(value)


def prepare_url(value: Url | AnyUrl) -> str:
    return str(value)


def prepare_email(value: NameEmail) -> str:
    return str(value)


def prepare_colour(value: Color) -> str:
    return str(value)


def prepare_pydantic_secret(value: SecretBytes | SecretStr) -> str:
    return str(value)


def prepare_re_pattern(value: Pattern[Any]) -> str:
    return value.pattern


SIMPLE_ENCODERS_BY_TYPE: Dict[Type[Any], Callable[[Any], Any]] = {
    Enum: prepare_enum,
    Decimal: prepare_decimal,
    UUID: prepare_uuid,
    # prepare_datetime
    datetime.date: prepare_datetime_date,
    datetime.datetime: prepare_datetime_date,
    datetime.time: prepare_datetime_date,
    datetime.timedelta: prepare_datetime_timedelta,
    # prepare_ip
    IPv4Address: prepare_ip,
    IPv4Interface: prepare_ip,
    IPv4Network: prepare_ip,
    IPv6Address: prepare_ip,
    IPv6Interface: prepare_ip,
    IPv6Network: prepare_ip,
    # re
    Pattern: prepare_re_pattern,
    # pydantic types
    Color: prepare_colour,
    NameEmail: prepare_email,
    Path: prepare_path,
    SecretBytes: prepare_pydantic_secret,
    SecretStr: prepare_pydantic_secret,
    Url: prepare_url,
    AnyUrl: prepare_url,
}


def get_encoders_by_class_tuples() -> Dict[Callable[[Any], Any], Tuple[Any, ...]]:
    encoders_by_cls_tuples: Dict[Callable[[Any], Any], Tuple[Any, ...]] = defaultdict(tuple)
    for type_, encoder in SIMPLE_ENCODERS_BY_TYPE.items():
        encoders_by_cls_tuples[encoder] += (type_,)
    return encoders_by_cls_tuples


encoders_by_class_tuples = get_encoders_by_class_tuples()


@overload
def jsonify(
    obj: Any,
    *,
    include: Include | None = ...,
    exclude: Exclude | None = ...,
    by_alias: bool = ...,
    exclude_unset: bool = ...,
    exclude_defaults: bool = ...,
    exclude_none: bool = ...,
    custom_encoder: CustomEncoder | None = ...,
    charset: str | Charset = ...,
    dumps: Literal[False] = ...,
    dumps_encoder: JSONEncoder = ...,
) -> Any: ...


@overload
def jsonify(
    obj: Any,
    *,
    include: Include | None = ...,
    exclude: Exclude | None = ...,
    by_alias: bool = ...,
    exclude_unset: bool = ...,
    exclude_defaults: bool = ...,
    exclude_none: bool = ...,
    custom_encoder: CustomEncoder | None = ...,
    charset: str | Charset = ...,
    dumps: Literal[True] = ...,
    dumps_encoder: JSONEncoder = ...,
) -> str: ...


@overload
def jsonify(
    obj: Any,
    *,
    include: Include | None = ...,
    exclude: Exclude | None = ...,
    by_alias: bool = ...,
    exclude_unset: bool = ...,
    exclude_defaults: bool = ...,
    exclude_none: bool = ...,
    custom_encoder: CustomEncoder | None = ...,
    charset: str | Charset = ...,
    dumps: bool = ...,
    dumps_encoder: JSONEncoder = ...,
) -> str | Any: ...


def jsonify(
    obj: Any,
    *,
    include: Include | None = None,
    exclude: Exclude | None = None,
    by_alias: bool = True,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    custom_encoder: CustomEncoder | None = None,
    charset: str | Charset = Charset.utf8,
    dumps: bool = False,
    dumps_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> str | Any:
    """Convert any object to something that can be encoded in JSON.

    This is used internally by `rapidy` to make sure anything you return can be
    encoded as JSON before it is sent to the client.

    You can also use it yourself, for example to convert objects before saving them
    in a database that supports only JSON.

    Args:
        obj:
            The input object something that can be encoded in JSON.
        include:
            Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
        exclude:
            Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
        by_alias:
            Pydantic's `by_alias` parameter, passed to Pydantic models to define
            if the output should use the alias names (when provided) or the Python
            attribute names. In an API, if you set an alias, it's probably because you
            want to use it in the result, so you probably want to leave this set to `True`.
        exclude_unset:
            Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that were not explicitly
            set (and that only had their default values).
        exclude_defaults:
            Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that had the same default
            value, even when they were explicitly set.
        exclude_none:
            Pydantic's `exclude_none` parameter, passed to Pydantic models to define
            if it should exclude from the output any fields that have a `None` value.
        custom_encoder:
            Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
        charset:
            The `charset` that will be used to encode and decode obj data.
        dumps:
            Arg that determines whether to make a string from the created object.
        dumps_encoder:
            Any callable that accepts an object and returns a JSON string.
            Will be used if jsonify(dumps=True, ...).

    Note:
        This code and doc is taken almost unchanged from the https://fastapi.tiangolo.com/ project.
    """
    result = _prepare_to_json(
        obj,
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        byte_preparation_charset=charset,
    )
    if dumps:
        return dumps_encoder(result)
    return result


def _prepare_to_json(  # noqa: PLR0912 C901
    obj: Any,
    *,
    include: Include | None,
    exclude: Exclude | None,
    by_alias: bool,
    exclude_unset: bool,
    exclude_defaults: bool,
    exclude_none: bool,
    custom_encoder: CustomEncoder | None,
    byte_preparation_charset: str,
) -> Any:
    custom_encoder = custom_encoder or {}  # TODO: tests  # noqa: FIX002
    if custom_encoder:
        if type(obj) in custom_encoder:
            return custom_encoder[type(obj)](obj)
        for encoder_type, encoder_instance in custom_encoder.items():
            if isinstance(obj, encoder_type):
                return encoder_instance(obj)

    if include is not None and not isinstance(include, set | dict):
        include = set(include)
    if exclude is not None and not isinstance(exclude, set | dict):
        exclude = set(exclude)

    if isinstance(obj, BaseModel):
        return prepare_base_model(
            obj,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            byte_preparation_charset=byte_preparation_charset,
        )

    if dataclasses.is_dataclass(obj):
        return prepare_dataclass(
            obj,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            byte_preparation_charset=byte_preparation_charset,
        )

    if isinstance(obj, dict):
        return prepare_dict(
            obj,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            byte_preparation_charset=byte_preparation_charset,
        )

    if isinstance(obj, MainSequenceTypes):
        return prepare_sequence(
            obj,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            byte_preparation_charset=byte_preparation_charset,
        )

    if isinstance(obj, bytes):
        return prepare_bytes(obj, charset=byte_preparation_charset)

    if type(obj) in SIMPLE_ENCODERS_BY_TYPE:
        return SIMPLE_ENCODERS_BY_TYPE[type(obj)](obj)

    for encoder, classes_tuple in encoders_by_class_tuples.items():
        if isinstance(obj, classes_tuple):
            return encoder(obj)

    if isinstance(obj, PassableTypes):
        return obj

    data = get_data_for_prepare_by_unknown_type(obj)

    return _prepare_to_json(
        data,
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        byte_preparation_charset=byte_preparation_charset,
    )


def prepare_base_model(
    obj: BaseModel,
    *,
    include: Include | None,
    exclude: Exclude | None,
    by_alias: bool,
    exclude_unset: bool,
    exclude_none: bool,
    exclude_defaults: bool,
    custom_encoder: CustomEncoder | None,
    byte_preparation_charset: str,
) -> Any:
    encoders: Dict[Any, Any] = {}
    if PYDANTIC_IS_V1:
        encoders = getattr(obj.__config__, 'json_encoders', {})
        if custom_encoder:
            encoders.update(custom_encoder)

    obj_dict = pydantic_model_dump(
        obj,
        mode='json',
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_none=exclude_none,
        exclude_defaults=exclude_defaults,
    )
    if '__root__' in obj_dict:
        obj_dict = obj_dict['__root__']

    return _prepare_to_json(
        obj_dict,
        include=None,
        exclude=None,
        by_alias=True,
        exclude_unset=False,
        exclude_none=exclude_none,
        exclude_defaults=exclude_defaults,
        custom_encoder=encoders,  # NOTE: only for p1
        byte_preparation_charset=byte_preparation_charset,
    )


def prepare_dataclass(
    obj: Any,
    *,
    include: Include | None,
    exclude: Exclude | None,
    by_alias: bool,
    exclude_unset: bool,
    exclude_none: bool,
    exclude_defaults: bool,
    custom_encoder: CustomEncoder | None,
    byte_preparation_charset: str,
) -> Any:
    obj_dict = dataclasses.asdict(obj)
    return _prepare_to_json(
        obj_dict,
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        byte_preparation_charset=byte_preparation_charset,
    )


def prepare_sequence(
    obj: MainSequence,
    *,
    include: Include | None,
    exclude: Exclude | None,
    by_alias: bool,
    exclude_unset: bool,
    exclude_none: bool,
    exclude_defaults: bool,
    custom_encoder: CustomEncoder | None,
    byte_preparation_charset: str,
) -> List[Any]:
    return [
        _prepare_to_json(
            item,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            byte_preparation_charset=byte_preparation_charset,
        )
        for item in obj
    ]


def prepare_dict(
    obj: Dict[Any, Any],
    *,
    include: Include | None,
    exclude: Exclude | None,
    by_alias: bool,
    exclude_unset: bool,
    exclude_none: bool,
    exclude_defaults: bool,
    custom_encoder: CustomEncoder | None,
    byte_preparation_charset: str,
) -> Dict[Any, Any]:
    encoded_dict = {}
    allowed_keys = set(obj.keys())
    if include is not None:
        allowed_keys &= set(include)

    if exclude is not None:
        allowed_keys -= set(exclude)

    for key, value in obj.items():
        if (value is not None or not exclude_none) and key in allowed_keys:
            # FIXME: partially does not support nested BaseModel (fastapi legacy)
            encoded_key = _prepare_to_json(
                key,
                include=None,
                exclude=None,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
                custom_encoder=custom_encoder,
                exclude_defaults=exclude_defaults,
                byte_preparation_charset=byte_preparation_charset,
            )
            encoded_value = _prepare_to_json(
                value,
                include=None,
                exclude=None,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
                custom_encoder=custom_encoder,
                exclude_defaults=exclude_defaults,
                byte_preparation_charset=byte_preparation_charset,
            )
            encoded_dict[encoded_key] = encoded_value

    return encoded_dict


def get_data_for_prepare_by_unknown_type(obj: Any) -> Any:
    try:
        data = dict(obj)
    except Exception as e:  # noqa: BLE001
        errors: List[Exception] = []
        errors.append(e)
        try:
            data = vars(obj)
        except Exception as e:
            errors.append(e)
            raise ValueError(errors) from e

    return data
