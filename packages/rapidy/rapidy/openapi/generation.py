from __future__ import annotations

import inspect
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from http import HTTPStatus
from typing import Annotated, Any, get_args, get_origin, Literal, TYPE_CHECKING

from pydantic import TypeAdapter
from rapidy_core.annotation_checkers import is_empty, is_union, lenient_issubclass
from rapidy_core.enums import ContentType, HTTPRequestParamType

from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.openapi.config import OpenAPIConfig
from rapidy.routing.http.routers import HandlerParameterRecord
from rapidy.routing.matcher import RouteRecord
from rapidy.typedefs import Unset

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

__all__ = ('OpenAPIGenerationError', 'create_openapi_schema')

_REF_TEMPLATE = '#/components/schemas/{model}'
_NO_BODY_STATUSES = {204, 304}
_VALIDATION_ERROR_SCHEMA = {
    'properties': {
        'loc': {'items': {'anyOf': [{'type': 'string'}, {'type': 'integer'}]}, 'type': 'array'},
        'msg': {'type': 'string'},
        'type': {'type': 'string'},
    },
    'required': ['loc', 'msg', 'type'],
    'title': 'RapidyValidationError',
    'type': 'object',
}
_HTTP_VALIDATION_ERROR_SCHEMA = {
    'properties': {
        'errors': {
            'items': {'$ref': '#/components/schemas/RapidyValidationError'},
            'type': 'array',
        },
    },
    'required': ['errors'],
    'title': 'RapidyHTTPValidationError',
    'type': 'object',
}


class OpenAPIGenerationError(ValueError):
    """Raised when registered routes cannot form one unambiguous OpenAPI document."""


class _SchemaRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, tuple[Literal['validation', 'serialization'], TypeAdapter[Any]]] = {}
        self._fallbacks: dict[str, dict[str, Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self.components: dict[str, dict[str, Any]] = {}

    def add(
        self,
        key: str,
        annotation: Any,
        *,
        field_info: FieldInfo | None = None,
        fallback: dict[str, Any] | None = None,
        mode: Literal['validation', 'serialization'] = 'validation',
    ) -> None:
        if is_empty(annotation):
            self._fallbacks[key] = fallback or {}
            return
        try:
            adapted_annotation: Any = Annotated[annotation, field_info] if field_info is not None else annotation
            self._adapters[key] = (mode, TypeAdapter(adapted_annotation))
        except (TypeError, ValueError):
            self._fallbacks[key] = fallback or _fallback_schema(annotation)

    def build(self) -> None:
        inputs: list[
            tuple[str, Literal['validation', 'serialization'], TypeAdapter[Any]]
        ] = [(key, mode, adapter) for key, (mode, adapter) in self._adapters.items()]
        if inputs:
            try:
                schemas, root = TypeAdapter.json_schemas(inputs, ref_template=_REF_TEMPLATE)
            except (TypeError, ValueError):
                self._build_individually()
            else:
                self._schemas.update(
                    {
                        key: deepcopy(schemas[(key, mode)])
                        for key, (mode, _adapter) in self._adapters.items()
                    }
                )
                self._merge_components(root.pop('$defs', {}))
        self._schemas.update({key: deepcopy(schema) for key, schema in self._fallbacks.items()})

    def _build_individually(self) -> None:
        for key, (mode, adapter) in self._adapters.items():
            try:
                schema = adapter.json_schema(mode=mode, ref_template=_REF_TEMPLATE)
            except (TypeError, ValueError):
                self._schemas[key] = {}
                continue
            self._merge_components(schema.pop('$defs', {}))
            self._schemas[key] = schema

    def _merge_components(self, schemas: Mapping[str, dict[str, Any]]) -> None:
        for name, schema in schemas.items():
            existing = self.components.get(name)
            if existing is not None and existing != schema:
                msg = f'Conflicting OpenAPI component schema name: {name!r}'
                raise OpenAPIGenerationError(msg)
            self.components[name] = schema

    def get(self, key: str) -> dict[str, Any]:
        return deepcopy(self._schemas[key])

    def resolve_object(self, schema: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = schema.get('$ref')
        if not isinstance(reference, str) or not reference.startswith('#/components/schemas/'):
            return schema
        return self.components.get(reference.rsplit('/', 1)[-1], schema)


def _fallback_schema(annotation: Any) -> dict[str, Any]:
    if annotation is bytes:
        return {'format': 'binary', 'type': 'string'}
    if annotation is str:
        return {'type': 'string'}
    if annotation is bool:
        return {'type': 'boolean'}
    if annotation is int:
        return {'type': 'integer'}
    if annotation is float:
        return {'type': 'number'}
    return {}


def _parameter_key(route_index: int, parameter_index: int) -> str:
    return f'route:{route_index}:parameter:{parameter_index}'


def _response_key(route_index: int) -> str:
    return f'route:{route_index}:response'


def _response_annotation(route: RouteRecord) -> Any:
    configured = route.route_kwargs.get('response_type', Unset)
    if configured is not Unset:
        annotation = configured
    else:
        try:
            annotation = get_http_handler_info(
                route.handler,
                request_attr_can_declare_fst=True,
            ).return_annotation
        except (TypeError, ValueError):
            annotation = inspect.signature(route.handler).return_annotation

    if annotation_is_stream_response(annotation):
        return inspect.Signature.empty
    if not is_union(annotation):
        return annotation
    filtered = tuple(item for item in get_args(annotation) if not annotation_is_stream_response(item))
    if not filtered:
        return inspect.Signature.empty
    annotation = filtered[0]
    for item in filtered[1:]:
        annotation |= item
    return annotation


def _find_parameter_end(path: str, start: int) -> int:
    depth = 1
    index = start + 1
    while index < len(path):
        character = path[index]
        if character == '\\':
            index += 2
            continue
        if character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _openapi_path(path: str) -> tuple[str, dict[str, str | None]]:
    chunks: list[str] = []
    parameters: dict[str, str | None] = {}
    literal_start = 0
    index = 0
    while index < len(path):
        if path[index] != '{':
            index += 1
            continue
        chunks.append(path[literal_start:index])
        end = _find_parameter_end(path, index)
        if end < 0:
            msg = f'Unclosed path parameter in {path!r}'
            raise OpenAPIGenerationError(msg)
        definition = path[index + 1 : end]
        name, separator, expression = definition.partition(':')
        parameters[name] = expression if separator else None
        chunks.append(f'{{{name}}}')
        index = end + 1
        literal_start = index
    chunks.append(path[literal_start:])
    return ''.join(chunks), parameters


def _route_is_included(route: RouteRecord) -> bool:
    return not route.is_auto_head and bool(route.route_kwargs.get('include_in_schema', True))


def _collect_schemas(routes: Sequence[RouteRecord], registry: _SchemaRegistry) -> None:
    for route_index, route in enumerate(routes):
        for parameter_index, parameter in enumerate(route.parameters):
            record = parameter
            if not isinstance(record, HandlerParameterRecord):
                continue
            fallback = (
                {'format': 'binary', 'type': 'string'}
                if record.param_type is HTTPRequestParamType.body
                and str(getattr(record.field_info, 'content_type', '')) == ContentType.stream
                else None
            )
            registry.add(
                _parameter_key(route_index, parameter_index),
                record.annotation,
                field_info=record.field_info,
                fallback=fallback,
            )
        registry.add(
            _response_key(route_index),
            _response_annotation(route),
            mode='serialization',
        )


def _parameter_description(schema: dict[str, Any], field_info: FieldInfo | None = None) -> str | None:
    description = schema.pop('description', None)
    if description is None and field_info is not None:
        description = field_info.description
    return str(description) if description is not None else None


def _single_parameter(
    record: HandlerParameterRecord,
    schema: dict[str, Any],
    *,
    name: str,
) -> dict[str, Any]:
    parameter: dict[str, Any] = {
        'in': record.param_type.value,
        'name': name,
        'required': record.param_type is HTTPRequestParamType.path or record.required,
        'schema': schema,
    }
    description = _parameter_description(schema, record.field_info)
    if description is not None:
        parameter['description'] = description
    deprecated = getattr(record.field_info, 'deprecated', None)
    if deprecated:
        parameter['deprecated'] = True
    return parameter


def _expand_parameter(
    record: HandlerParameterRecord,
    schema: dict[str, Any],
    registry: _SchemaRegistry,
) -> list[dict[str, Any]]:
    resolved = registry.resolve_object(schema)
    properties = resolved.get('properties')
    if record.extract_single or not isinstance(properties, Mapping):
        name = record.alias or record.name
        parameter = _single_parameter(record, schema, name=name)
        if not record.extract_single and record.param_type is HTTPRequestParamType.query:
            parameter['style'] = 'deepObject'
            parameter['explode'] = True
        return [parameter]

    required = set(resolved.get('required', ()))
    result: list[dict[str, Any]] = []
    for name, property_schema in properties.items():
        current_schema = deepcopy(property_schema)
        current: dict[str, Any] = {
            'in': record.param_type.value,
            'name': name,
            'required': record.param_type is HTTPRequestParamType.path or name in required,
            'schema': current_schema,
        }
        description = _parameter_description(current_schema)
        if description is not None:
            current['description'] = description
        result.append(current)
    return result


def _operation_parameters(
    route_index: int,
    route: RouteRecord,
    path_parameters: Mapping[str, str | None],
    registry: _SchemaRegistry,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for parameter_index, parameter in enumerate(route.parameters):
        if not isinstance(parameter, HandlerParameterRecord):
            continue
        if parameter.param_type is HTTPRequestParamType.body:
            continue
        schema = registry.get(_parameter_key(route_index, parameter_index))
        for item in _expand_parameter(parameter, schema, registry):
            identifier = (item['name'], item['in'])
            if identifier in seen:
                msg = f'Duplicate OpenAPI parameter {identifier!r} for {route.method} {route.path}'
                raise OpenAPIGenerationError(msg)
            seen.add(identifier)
            result.append(item)

    for name, pattern in path_parameters.items():
        identifier = (name, HTTPRequestParamType.path.value)
        if identifier in seen:
            continue
        missing_schema: dict[str, Any] = {'type': 'string'}
        if pattern is not None:
            missing_schema['pattern'] = pattern
        result.append({'in': 'path', 'name': name, 'required': True, 'schema': missing_schema})
        seen.add(identifier)
    return result


def _request_body(route_index: int, route: RouteRecord, registry: _SchemaRegistry) -> dict[str, Any] | None:
    body_parameters = [
        (parameter_index, parameter)
        for parameter_index, parameter in enumerate(route.parameters)
        if isinstance(parameter, HandlerParameterRecord) and parameter.param_type is HTTPRequestParamType.body
    ]
    if not body_parameters:
        return None
    if len(body_parameters) > 1:
        msg = f'Multiple body parameters cannot be represented for {route.method} {route.path}'
        raise OpenAPIGenerationError(msg)

    parameter_index, parameter = body_parameters[0]
    schema = registry.get(_parameter_key(route_index, parameter_index))
    description = _parameter_description(schema, parameter.field_info)
    content_type = str(getattr(parameter.field_info, 'content_type', ContentType.json))
    request_body: dict[str, Any] = {
        'content': {content_type: {'schema': schema}},
        'required': parameter.required,
    }
    if description is not None:
        request_body['description'] = description
    return request_body


def _response_content_type(annotation: Any, configured: Any) -> str:
    if configured is not None:
        return str(configured)
    if annotation is bytes:
        return ContentType.stream.value
    origin = get_origin(annotation)
    if origin in (dict, list, tuple, set, frozenset) or lenient_issubclass(annotation, Mapping):
        return ContentType.json.value
    if annotation in (str, int, float, bool):
        return ContentType.text_plain.value
    return ContentType.json.value


def _status_description(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return 'Response'


def _responses(route_index: int, route: RouteRecord, registry: _SchemaRegistry) -> dict[str, Any]:
    status_code = int(route.route_kwargs.get('status_code', HTTPStatus.OK))
    description = route.route_kwargs.get('response_description') or _status_description(status_code)
    response: dict[str, Any] = {'description': str(description)}
    annotation = _response_annotation(route)
    if status_code not in _NO_BODY_STATUSES and annotation not in (None, type(None)) and not is_empty(annotation):
        content_type = _response_content_type(annotation, route.route_kwargs.get('response_content_type'))
        response['content'] = {content_type: {'schema': registry.get(_response_key(route_index))}}

    result: dict[str, Any] = {str(status_code): response}
    if route.parameters:
        result['422'] = {
            'content': {
                ContentType.json.value: {
                    'schema': {'$ref': '#/components/schemas/RapidyHTTPValidationError'},
                },
            },
            'description': HTTPStatus.UNPROCESSABLE_ENTITY.phrase,
        }
    configured = route.route_kwargs.get('responses')
    if isinstance(configured, Mapping):
        for configured_status, configured_response in configured.items():
            if not isinstance(configured_response, Mapping):
                msg = f'OpenAPI response {configured_status!r} must be a mapping'
                raise OpenAPIGenerationError(msg)
            result[str(configured_status)] = deepcopy(dict(configured_response))
    return result


def _default_operation_id(route: RouteRecord, openapi_path: str) -> str:
    handler_name = getattr(route.handler, '__name__', route.handler.__class__.__name__)
    path_name = re.sub(r'[^a-zA-Z0-9]+', '_', openapi_path).strip('_')
    suffix = f'_{path_name}' if path_name else ''
    return f'{handler_name}_{route.method.lower()}{suffix}'


def _operation(
    route_index: int,
    route: RouteRecord,
    openapi_path: str,
    path_parameters: Mapping[str, str | None],
    registry: _SchemaRegistry,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        'operationId': route.route_kwargs.get('operation_id') or _default_operation_id(route, openapi_path),
        'responses': _responses(route_index, route, registry),
    }
    summary = route.route_kwargs.get('summary')
    if summary is None:
        handler_name = getattr(route.handler, '__name__', '')
        summary = handler_name.replace('_', ' ').strip().title() or None
    if summary is not None:
        operation['summary'] = str(summary)

    description = route.route_kwargs.get('description')
    if description is None:
        description = inspect.getdoc(route.handler)
    if description:
        operation['description'] = str(description)

    tags = route.route_kwargs.get('tags')
    if tags:
        operation['tags'] = list(tags)
    if route.route_kwargs.get('deprecated'):
        operation['deprecated'] = True

    parameters = _operation_parameters(route_index, route, path_parameters, registry)
    if parameters:
        operation['parameters'] = parameters
    request_body = _request_body(route_index, route, registry)
    if request_body is not None:
        operation['requestBody'] = request_body
    return operation


def _info(config: OpenAPIConfig) -> dict[str, Any]:
    info: dict[str, Any] = {'title': config.title, 'version': config.version}
    optional = {
        'description': config.description,
        'summary': config.summary,
        'termsOfService': config.terms_of_service,
        'contact': dict(config.contact) if config.contact is not None else None,
        'license': dict(config.license) if config.license is not None else None,
    }
    info.update({key: value for key, value in optional.items() if value is not None})
    return info


def create_openapi_schema(
    routes: Sequence[RouteRecord],
    config: OpenAPIConfig | None = None,
) -> dict[str, Any]:
    """Build a deterministic OpenAPI 3.1 document from rAPIdy's public route registry."""
    current_config = config or OpenAPIConfig()
    included_routes = tuple(route for route in routes if _route_is_included(route))
    registry = _SchemaRegistry()
    _collect_schemas(included_routes, registry)
    registry.build()

    paths: dict[str, dict[str, Any]] = {}
    operation_ids: set[str] = set()
    has_validation = False
    for route_index, route in enumerate(included_routes):
        openapi_path, path_parameters = _openapi_path(route.path)
        method = route.method.lower()
        path_item = paths.setdefault(openapi_path, {})
        if method in path_item:
            msg = f'Conflicting OpenAPI operation for {route.method} {openapi_path}'
            raise OpenAPIGenerationError(msg)
        operation = _operation(route_index, route, openapi_path, path_parameters, registry)
        operation_id = operation['operationId']
        if operation_id in operation_ids:
            msg = f'Duplicate OpenAPI operationId: {operation_id!r}'
            raise OpenAPIGenerationError(msg)
        operation_ids.add(operation_id)
        path_item[method] = operation
        has_validation = has_validation or bool(route.parameters)

    components = dict(registry.components)
    if has_validation:
        for name, validation_schema in (
            ('RapidyValidationError', _VALIDATION_ERROR_SCHEMA),
            ('RapidyHTTPValidationError', _HTTP_VALIDATION_ERROR_SCHEMA),
        ):
            if name in components and components[name] != validation_schema:
                msg = f'OpenAPI component name {name!r} is reserved by rAPIdy'
                raise OpenAPIGenerationError(msg)
            components[name] = deepcopy(validation_schema)

    schema: dict[str, Any] = {
        'openapi': '3.1.0',
        'info': _info(current_config),
        'paths': paths,
    }
    if components:
        schema['components'] = {'schemas': components}
    if current_config.servers:
        schema['servers'] = [dict(server) for server in current_config.servers]
    if current_config.tags:
        schema['tags'] = [dict(tag) for tag in current_config.tags]
    return schema
