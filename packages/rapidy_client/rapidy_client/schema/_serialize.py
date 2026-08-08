from __future__ import annotations

import json as _json
import types
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.encoders import CustomEncoder, Exclude, Include, jsonify
from rapidy_core.typedefs import JSONEncoder

from rapidy_client._models import QueryValue, Response, Result
from rapidy_client.errors import (
    DecodeError,
    ResponseValidationError,
    SchemaDefinitionError,
    StatusError,
)

if TYPE_CHECKING:
    from rapidy_client.schema import ListStyle


def _scalar_to_str(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        normalized = (
            value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        )
        return normalized.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _scalar_to_str(value.value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _is_scalar_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _query_uses_csv(list_style: ListStyle | None) -> bool:
    return list_style is not None and getattr(list_style, "value", "repeat") == "csv"


def serialize_query(
    values: Mapping[str, QueryValue],
    *,
    list_style: ListStyle | None = None,
) -> list[tuple[str, str]]:
    use_csv = _query_uses_csv(list_style)
    serialized: list[tuple[str, str]] = []
    for key, value in values.items():
        if value is None:
            continue
        if _is_scalar_sequence(value):
            sequence = typing.cast(Sequence[QueryValue], value)
            parts = [_scalar_to_str(item) for item in sequence if item is not None]
            if not parts:
                continue
            if use_csv:
                serialized.append((key, ",".join(parts)))
            else:
                serialized.extend((key, part) for part in parts)
        else:
            serialized.append((key, _scalar_to_str(value)))
    return serialized


def expand_param_model(
    model: BaseModel,
    *,
    by_alias: bool = True,
    exclude_none: bool = True,
) -> dict[str, object]:
    return dict(
        model.model_dump(mode="json", by_alias=by_alias, exclude_none=exclude_none)
    )


def serialize_headers(items: Mapping[str, object]) -> list[tuple[str, str]]:
    return [
        (name, _scalar_to_str(value))
        for name, value in items.items()
        if value is not None
    ]


def serialize_cookies(items: Mapping[str, object]) -> str:
    return "; ".join(
        f"{name}={_scalar_to_str(value)}"
        for name, value in items.items()
        if value is not None
    )


def _is_json_content_type(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def resolve_content_type(
    *,
    body_marker_content_type: str | None = None,
    request_content_type: str | None = None,
) -> str:
    if body_marker_content_type is not None:
        return body_marker_content_type
    if request_content_type is not None:
        return request_content_type
    return "application/json"


def serialize_body(
    obj: object,
    *,
    content_type: str,
    request_include_fields: Include | None = None,
    request_exclude_fields: Exclude | None = None,
    request_by_alias: bool = True,
    request_exclude_unset: bool = False,
    request_exclude_defaults: bool = False,
    request_exclude_none: bool = False,
    request_custom_encoder: CustomEncoder | None = None,
    request_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
    request_charset: str = "utf-8",
) -> bytes:
    if _is_json_content_type(content_type):
        text = jsonify(
            obj,
            include=request_include_fields,
            exclude=request_exclude_fields,
            by_alias=request_by_alias,
            exclude_unset=request_exclude_unset,
            exclude_defaults=request_exclude_defaults,
            exclude_none=request_exclude_none,
            custom_encoder=request_custom_encoder,
            charset=request_charset,
            dumps=True,
            dumps_encoder=request_json_encoder,
        )
        return text.encode(request_charset)
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    if isinstance(obj, str):
        return obj.encode(request_charset)
    raise SchemaDefinitionError(
        f"body with Content-Type={content_type!r} must be bytes or str, "
        f"got {type(obj).__name__}"
    )


class ResponseKind(Enum):
    NONE = "none"
    RAW = "raw"
    STREAM = "stream"
    MODEL = "model"


type ErrorModel = type[BaseModel] | Mapping[int, type[BaseModel]] | None


@dataclass(slots=True, kw_only=True)
class ResponsePlan:
    kind: ResponseKind
    model: type[BaseModel] | None = None
    response_validate: bool = True
    statuses: dict[int, type[BaseModel] | None] = field(default_factory=dict)
    error_model: ErrorModel = None
    wrap_result: bool = False


def _is_model_type(value: object) -> bool:
    return isinstance(value, type) and issubclass(value, BaseModel)


def _is_stream_annotation(annotation: object) -> bool:
    from rapidy_client.schema import Stream

    return annotation is Stream or typing.get_origin(annotation) is Stream


def _extract_model(annotation: object) -> type[BaseModel] | None:
    if _is_model_type(annotation):
        return typing.cast(type[BaseModel], annotation)
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        for argument in typing.get_args(annotation):
            if _is_model_type(argument):
                return typing.cast(type[BaseModel], argument)
    return None


def _assert_statuses_error_model_disjoint(
    statuses: Mapping[int, type[BaseModel] | None],
    error_model: ErrorModel,
) -> None:
    if isinstance(error_model, Mapping):
        overlap = set(statuses) & set(error_model)
        if overlap:
            raise SchemaDefinitionError(
                f"status code occurs in statuses and error_model: {sorted(overlap)}"
            )


def build_response_plan(
    *,
    return_annotation: object,
    response_validate: bool = True,
    response_type: type[BaseModel] | None = None,
    statuses: Mapping[int, type[BaseModel] | None] | None = None,
    error_model: ErrorModel = None,
) -> ResponsePlan:
    statuses_map = dict(statuses or {})
    invalid_statuses = {
        status
        for status in statuses_map
        if not isinstance(status, int) or not 100 <= status <= 599
    }
    if invalid_statuses:
        raise SchemaDefinitionError(
            f"invalid status code(s) in statuses: {sorted(invalid_statuses, key=str)}"
        )
    invalid_values = {
        status: value
        for status, value in statuses_map.items()
        if value is not None and not _is_model_type(value)
    }
    if invalid_values:
        raise SchemaDefinitionError(
            f"statuses values must be pydantic model types or None: {invalid_values}"
        )
    if response_type is not None and not _is_model_type(response_type):
        raise SchemaDefinitionError("response_type must be a pydantic model type")
    if error_model is not None:
        error_types = (
            error_model.values() if isinstance(error_model, Mapping) else (error_model,)
        )
        if any(not _is_model_type(item) for item in error_types):
            raise SchemaDefinitionError(
                "error_model values must be pydantic model types"
            )
    _assert_statuses_error_model_disjoint(statuses_map, error_model)

    annotation = return_annotation
    wrap_result = False
    if typing.get_origin(annotation) is Result:
        arguments = typing.get_args(annotation)
        if len(arguments) != 1:
            raise SchemaDefinitionError("Result requires exactly one type argument")
        annotation = arguments[0]
        wrap_result = True

    if wrap_result and (annotation is Response or _is_stream_annotation(annotation)):
        raise SchemaDefinitionError("Result[Response] and Result[Stream] are forbidden")

    if response_type is not None:
        kind = ResponseKind.MODEL
        model = response_type
    elif annotation is None or annotation is type(None):
        kind = ResponseKind.NONE
        model = None
    elif annotation is Response:
        kind = ResponseKind.RAW
        model = None
    elif _is_stream_annotation(annotation):
        if statuses_map:
            raise SchemaDefinitionError("Stream does not support statuses values")
        kind = ResponseKind.STREAM
        model = None
    else:
        kind = ResponseKind.MODEL
        model = _extract_model(annotation)
        if model is None:
            raise SchemaDefinitionError(
                f"unsupported return annotation: {annotation!r}; expected a pydantic "
                "model, Response, Stream, None, or Result[T]"
            )

    return ResponsePlan(
        kind=kind,
        model=model,
        response_validate=response_validate,
        statuses=statuses_map,
        error_model=error_model,
        wrap_result=wrap_result,
    )


def _load_model_from_bytes(
    model: type[BaseModel], data: bytes, *, validate: bool
) -> BaseModel:
    if validate:
        try:
            return model.model_validate_json(data)
        except ValidationError as exc:
            raise ResponseValidationError(str(exc)) from exc
    try:
        raw = _json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise DecodeError("invalid JSON response body") from exc
    if isinstance(raw, dict):
        return model.model_construct(**raw)
    return model.model_construct()


async def _read_and_close(response: Response, *, limit: int | None = None) -> bytes:
    try:
        if limit is None:
            return await response.aread()
        return await response._aread_capped(limit)
    finally:
        await response.aclose()


async def _parse_model(
    response: Response, model: type[BaseModel], *, validate: bool
) -> BaseModel:
    data = await _read_and_close(response)
    return _load_model_from_bytes(model, data, validate=validate)


async def parse_response(
    response: Response,
    plan: ResponsePlan,
    *,
    error_body_limit: int = 65536,
) -> Any:
    def finish(value: Any) -> Any:
        if plan.wrap_result:
            return Result(
                value=value,
                status=response.status,
                headers=response.headers,
            )
        return value

    if plan.kind is ResponseKind.RAW:
        await _read_and_close(response)
        return response
    if plan.kind is ResponseKind.STREAM:
        raise NotImplementedError("lazy Stream parsing is implemented in milestone 18")

    status = response.status
    if status in plan.statuses:
        value_model = plan.statuses[status]
        if value_model is None:
            await _read_and_close(response)
            return finish(None)
        return finish(
            await _parse_model(response, value_model, validate=plan.response_validate)
        )

    if response.is_success:
        if plan.kind is ResponseKind.NONE:
            await _read_and_close(response)
            return finish(None)
        assert plan.model is not None
        return finish(
            await _parse_model(response, plan.model, validate=plan.response_validate)
        )

    error_body = await _read_and_close(response, limit=error_body_limit)
    if isinstance(plan.error_model, Mapping):
        error_type = plan.error_model.get(status)
    else:
        error_type = plan.error_model
    parsed_error: BaseModel | None = None
    if error_type is not None:
        try:
            parsed_error = _load_model_from_bytes(error_type, error_body, validate=True)
        except (ResponseValidationError, DecodeError, ValueError):
            parsed_error = None
    extensions = response.request.extensions
    raise StatusError(
        f"HTTP response status {status}",
        status=status,
        response=response,
        error_model=parsed_error,
        upstream=extensions.upstream,
        endpoint=extensions.endpoint,
        request_id=extensions.request_id,
    )


__all__ = (
    "ResponseKind",
    "ResponsePlan",
    "build_response_plan",
    "expand_param_model",
    "parse_response",
    "resolve_content_type",
    "serialize_body",
    "serialize_cookies",
    "serialize_headers",
    "serialize_query",
)
