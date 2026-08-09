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
_SECURITY_SCHEME_TYPES = frozenset({'apiKey', 'http', 'mutualTLS', 'oauth2', 'openIdConnect'})
_COMPONENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9.\-_]+$')
_COMPONENT_SECTIONS = (
    ('schemas', 'schemas'),
    ('responses', 'responses'),
    ('parameters', 'parameters'),
    ('examples', 'examples'),
    ('request_bodies', 'requestBodies'),
    ('headers', 'headers'),
    ('security_schemes', 'securitySchemes'),
    ('links', 'links'),
    ('callbacks', 'callbacks'),
    ('path_items', 'pathItems'),
)
_NON_ARRAY_TYPES = (str, bytes, bytearray)
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
        inputs: list[tuple[str, Literal['validation', 'serialization'], TypeAdapter[Any]]] = [
            (key, mode, adapter) for key, (mode, adapter) in self._adapters.items()
        ]
        if inputs:
            try:
                schemas, root = TypeAdapter.json_schemas(inputs, ref_template=_REF_TEMPLATE)
            except (TypeError, ValueError):
                self._build_individually()
            else:
                self._schemas.update(
                    {key: deepcopy(schemas[(key, mode)]) for key, (mode, _adapter) in self._adapters.items()}
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


def _named_openapi_objects(configured: Any, *, context: str) -> dict[str, dict[str, Any]]:
    if not isinstance(configured, Mapping):
        msg = f'OpenAPI {context} must be a mapping'
        raise OpenAPIGenerationError(msg)

    result: dict[str, dict[str, Any]] = {}
    for name, value in configured.items():
        if not isinstance(name, str) or not name:
            msg = f'OpenAPI {context} name must be a non-empty string: {name!r}'
            raise OpenAPIGenerationError(msg)
        if not isinstance(value, Mapping):
            msg = f'OpenAPI {context} {name!r} must be a mapping'
            raise OpenAPIGenerationError(msg)
        result[name] = deepcopy(dict(value))
    return result


def _validate_reference(value: Mapping[str, Any], *, context: str) -> bool:
    if '$ref' not in value:
        return False
    reference = value['$ref']
    if not isinstance(reference, str) or not reference:
        msg = f'OpenAPI {context} has an invalid `$ref`'
        raise OpenAPIGenerationError(msg)
    return True


def _response_links(
    configured: Any,
    *,
    context: str,
    referenced_operation_ids: set[str],
) -> dict[str, dict[str, Any]]:
    links = _named_openapi_objects(configured, context=f'response links for {context}')
    for name, link in links.items():
        if _validate_reference(link, context=f'response link {name!r} for {context}'):
            continue

        operation_id = link.get('operationId')
        operation_ref = link.get('operationRef')
        has_operation_id = isinstance(operation_id, str) and bool(operation_id)
        has_operation_ref = isinstance(operation_ref, str) and bool(operation_ref)
        if has_operation_id == has_operation_ref:
            msg = (
                f'OpenAPI response link {name!r} for {context} must define exactly one of '
                '`operationId` or `operationRef`'
            )
            raise OpenAPIGenerationError(msg)
        if operation_id is not None and not has_operation_id:
            msg = f'OpenAPI response link {name!r} for {context} has an invalid `operationId`'
            raise OpenAPIGenerationError(msg)
        if operation_ref is not None and not has_operation_ref:
            msg = f'OpenAPI response link {name!r} for {context} has an invalid `operationRef`'
            raise OpenAPIGenerationError(msg)
        if isinstance(operation_id, str) and operation_id:
            referenced_operation_ids.add(operation_id)
        if 'parameters' in link and not isinstance(link['parameters'], Mapping):
            msg = f'OpenAPI response link {name!r} for {context} has invalid `parameters`'
            raise OpenAPIGenerationError(msg)
        if 'server' in link and not isinstance(link['server'], Mapping):
            msg = f'OpenAPI response link {name!r} for {context} has an invalid `server`'
            raise OpenAPIGenerationError(msg)
    return links


def _callbacks(configured: Any, *, context: str) -> dict[str, dict[str, Any]]:
    callbacks = _named_openapi_objects(configured, context=f'callbacks for {context}')
    for name, callback in callbacks.items():
        if _validate_reference(callback, context=f'callback {name!r} for {context}'):
            continue
        for expression, path_item in callback.items():
            if not isinstance(expression, str) or not expression:
                msg = f'OpenAPI callback expression for {name!r} in {context} must be a non-empty string'
                raise OpenAPIGenerationError(msg)
            if expression.startswith('x-'):
                continue
            if not isinstance(path_item, Mapping):
                msg = f'OpenAPI callback path item for {name!r} in {context} must be a mapping'
                raise OpenAPIGenerationError(msg)
    return callbacks


def _operation_callback_section(route: RouteRecord) -> dict[str, Any]:
    configured = route.route_kwargs.get('callbacks', Unset)
    if configured is Unset:
        return {}
    callbacks = _callbacks(configured, context=f'{route.method} {route.path}')
    return {'callbacks': callbacks} if callbacks else {}


def _webhooks(config: OpenAPIConfig) -> dict[str, dict[str, Any]]:
    webhooks = _named_openapi_objects(config.webhooks, context='webhooks')
    for name, path_item in webhooks.items():
        _validate_reference(path_item, context=f'webhook {name!r}')
    return webhooks


def _responses(
    route_index: int,
    route: RouteRecord,
    registry: _SchemaRegistry,
    *,
    referenced_operation_ids: set[str],
) -> dict[str, Any]:
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

    configured_links = route.route_kwargs.get('response_links', Unset)
    if configured_links is not Unset:
        links = _response_links(
            configured_links,
            context=f'{route.method} {route.path}',
            referenced_operation_ids=referenced_operation_ids,
        )
        if links:
            primary_response = result[str(status_code)]
            if '$ref' in primary_response:
                msg = f'OpenAPI response links cannot be added to a referenced response for {route.method} {route.path}'
                raise OpenAPIGenerationError(msg)
            primary_response['links'] = links
    return result


def _default_operation_id(route: RouteRecord, openapi_path: str) -> str:
    handler_name = getattr(route.handler, '__name__', route.handler.__class__.__name__)
    path_name = re.sub(r'[^a-zA-Z0-9]+', '_', openapi_path).strip('_')
    suffix = f'_{path_name}' if path_name else ''
    return f'{handler_name}_{route.method.lower()}{suffix}'


def _is_array(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, _NON_ARRAY_TYPES)


def _validate_api_key_security_scheme(name: str, scheme: Mapping[str, Any]) -> None:
    if not isinstance(scheme.get('name'), str) or not scheme['name']:
        msg = f'OpenAPI apiKey security scheme {name!r} requires a non-empty `name`'
        raise OpenAPIGenerationError(msg)
    location = scheme.get('in')
    if not isinstance(location, str) or location not in {'query', 'header', 'cookie'}:
        msg = f'OpenAPI apiKey security scheme {name!r} has an invalid `in` value'
        raise OpenAPIGenerationError(msg)


def _validate_http_security_scheme(name: str, scheme: Mapping[str, Any]) -> None:
    if not isinstance(scheme.get('scheme'), str) or not scheme['scheme']:
        msg = f'OpenAPI http security scheme {name!r} requires a non-empty `scheme`'
        raise OpenAPIGenerationError(msg)


def _validate_openid_security_scheme(name: str, scheme: Mapping[str, Any]) -> None:
    url = scheme.get('openIdConnectUrl')
    if not isinstance(url, str) or not url:
        msg = f'OpenAPI openIdConnect security scheme {name!r} requires `openIdConnectUrl`'
        raise OpenAPIGenerationError(msg)


def _validate_security_scheme(name: str, scheme: Mapping[str, Any]) -> None:
    reference = scheme.get('$ref')
    if reference is not None:
        if not isinstance(reference, str) or not reference:
            msg = f'OpenAPI security scheme {name!r} has an invalid `$ref`'
            raise OpenAPIGenerationError(msg)
        return

    scheme_type = scheme.get('type')
    if not isinstance(scheme_type, str) or scheme_type not in _SECURITY_SCHEME_TYPES:
        msg = f'OpenAPI security scheme {name!r} has an unsupported type: {scheme_type!r}'
        raise OpenAPIGenerationError(msg)
    if scheme_type == 'apiKey':
        _validate_api_key_security_scheme(name, scheme)
    elif scheme_type == 'http':
        _validate_http_security_scheme(name, scheme)
    elif scheme_type == 'oauth2' and not isinstance(scheme.get('flows'), Mapping):
        msg = f'OpenAPI oauth2 security scheme {name!r} requires a `flows` mapping'
        raise OpenAPIGenerationError(msg)
    elif scheme_type == 'openIdConnect':
        _validate_openid_security_scheme(name, scheme)


def _configured_component_sections(config: OpenAPIConfig) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for attribute_name, openapi_name in _COMPONENT_SECTIONS:
        configured = getattr(config.components, attribute_name)
        if not isinstance(configured, Mapping):
            msg = f'OpenAPI components.{attribute_name} must be a mapping'
            raise OpenAPIGenerationError(msg)

        objects: dict[str, Any] = {}
        for name, value in configured.items():
            if not isinstance(name, str) or _COMPONENT_NAME_PATTERN.fullmatch(name) is None:
                msg = f'Invalid OpenAPI component name in {openapi_name}: {name!r}'
                raise OpenAPIGenerationError(msg)
            if openapi_name == 'schemas' and isinstance(value, bool):
                objects[name] = value
                continue
            if not isinstance(value, Mapping):
                msg = f'OpenAPI components.{openapi_name}.{name} must be a mapping'
                raise OpenAPIGenerationError(msg)
            objects[name] = deepcopy(dict(value))
        if objects:
            sections[openapi_name] = objects
    return sections


def _security_schemes(
    config: OpenAPIConfig,
    component_schemes: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for configured_schemes in (component_schemes, config.security_schemes):
        for name, configured_scheme in configured_schemes.items():
            if not isinstance(name, str) or _COMPONENT_NAME_PATTERN.fullmatch(name) is None:
                msg = f'Invalid OpenAPI security scheme component name: {name!r}'
                raise OpenAPIGenerationError(msg)
            if not isinstance(configured_scheme, Mapping):
                msg = f'OpenAPI security scheme {name!r} must be a mapping'
                raise OpenAPIGenerationError(msg)

            scheme = deepcopy(dict(configured_scheme))
            _validate_security_scheme(name, scheme)
            existing = result.get(name)
            if existing is not None and existing != scheme:
                msg = f'Conflicting OpenAPI security scheme component: {name!r}'
                raise OpenAPIGenerationError(msg)
            result[name] = scheme
    return result


def _security_requirements(
    configured: Any,
    scheme_names: set[str],
    *,
    context: str,
) -> list[dict[str, list[str]]]:
    if not _is_array(configured):
        msg = f'OpenAPI security requirements for {context} must be a sequence'
        raise OpenAPIGenerationError(msg)

    requirements: list[dict[str, list[str]]] = []
    for requirement in configured:
        if not isinstance(requirement, Mapping):
            msg = f'Each OpenAPI security requirement for {context} must be a mapping'
            raise OpenAPIGenerationError(msg)
        normalized: dict[str, list[str]] = {}
        for scheme_name, configured_scopes in requirement.items():
            if not isinstance(scheme_name, str) or not scheme_name:
                msg = f'OpenAPI security scheme reference for {context} must be a non-empty string'
                raise OpenAPIGenerationError(msg)
            if scheme_name not in scheme_names:
                msg = f'Unknown OpenAPI security scheme {scheme_name!r} referenced by {context}'
                raise OpenAPIGenerationError(msg)
            if not _is_array(configured_scopes) or not all(isinstance(scope, str) for scope in configured_scopes):
                msg = f'OpenAPI security scopes for {scheme_name!r} in {context} must be a sequence of strings'
                raise OpenAPIGenerationError(msg)
            normalized[scheme_name] = list(configured_scopes)
        requirements.append(normalized)
    return requirements


def _operation(
    route_index: int,
    route: RouteRecord,
    openapi_path: str,
    path_parameters: Mapping[str, str | None],
    registry: _SchemaRegistry,
    *,
    security_scheme_names: set[str],
    referenced_operation_ids: set[str],
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        'operationId': route.route_kwargs.get('operation_id') or _default_operation_id(route, openapi_path),
        'responses': _responses(
            route_index,
            route,
            registry,
            referenced_operation_ids=referenced_operation_ids,
        ),
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

    configured_security = route.route_kwargs.get('security', Unset)
    if configured_security is not Unset:
        operation['security'] = _security_requirements(
            configured_security,
            security_scheme_names,
            context=f'{route.method} {route.path}',
        )

    parameters = _operation_parameters(route_index, route, path_parameters, registry)
    if parameters:
        operation['parameters'] = parameters
    request_body = _request_body(route_index, route, registry)
    if request_body is not None:
        operation['requestBody'] = request_body
    operation.update(_operation_callback_section(route))
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


def _component_schemas(
    registry: _SchemaRegistry,
    *,
    configured_schemas: Mapping[str, Any],
    has_validation: bool,
) -> dict[str, Any]:
    schemas = dict(registry.components)
    for name, schema in configured_schemas.items():
        existing = schemas.get(name)
        if existing is not None and existing != schema:
            msg = f'Conflicting OpenAPI component schema name: {name!r}'
            raise OpenAPIGenerationError(msg)
        schemas[name] = deepcopy(schema)
    if has_validation:
        for name, validation_schema in (
            ('RapidyValidationError', _VALIDATION_ERROR_SCHEMA),
            ('RapidyHTTPValidationError', _HTTP_VALIDATION_ERROR_SCHEMA),
        ):
            if name in schemas and schemas[name] != validation_schema:
                msg = f'OpenAPI component name {name!r} is reserved by rAPIdy'
                raise OpenAPIGenerationError(msg)
            schemas[name] = deepcopy(validation_schema)
    return schemas


def _components(
    registry: _SchemaRegistry,
    *,
    configured_components: Mapping[str, Mapping[str, Any]],
    has_validation: bool,
    security_schemes: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    schemas = _component_schemas(
        registry,
        configured_schemas=configured_components.get('schemas', {}),
        has_validation=has_validation,
    )

    sections: dict[str, Any] = {}
    if schemas:
        sections['schemas'] = schemas
    for _attribute_name, openapi_name in _COMPONENT_SECTIONS[1:]:
        if openapi_name == 'securitySchemes':
            if security_schemes:
                sections[openapi_name] = dict(security_schemes)
            continue
        configured = configured_components.get(openapi_name)
        if configured:
            sections[openapi_name] = deepcopy(dict(configured))
    return sections


def create_openapi_schema(
    routes: Sequence[RouteRecord],
    config: OpenAPIConfig | None = None,
) -> dict[str, Any]:
    """Build a deterministic OpenAPI 3.1 document from rAPIdy's public route registry."""
    current_config = config or OpenAPIConfig()
    webhooks = _webhooks(current_config)
    configured_components = _configured_component_sections(current_config)
    security_schemes = _security_schemes(
        current_config,
        configured_components.get('securitySchemes', {}),
    )
    security_scheme_names = set(security_schemes)
    security = _security_requirements(
        current_config.security,
        security_scheme_names,
        context='the OpenAPI document',
    )
    included_routes = tuple(route for route in routes if _route_is_included(route))
    registry = _SchemaRegistry()
    _collect_schemas(included_routes, registry)
    registry.build()

    paths: dict[str, dict[str, Any]] = {}
    operation_ids: set[str] = set()
    referenced_operation_ids: set[str] = set()
    has_validation = False
    for route_index, route in enumerate(included_routes):
        openapi_path, path_parameters = _openapi_path(route.path)
        method = route.method.lower()
        path_item = paths.setdefault(openapi_path, {})
        if method in path_item:
            msg = f'Conflicting OpenAPI operation for {route.method} {openapi_path}'
            raise OpenAPIGenerationError(msg)
        operation = _operation(
            route_index,
            route,
            openapi_path,
            path_parameters,
            registry,
            security_scheme_names=security_scheme_names,
            referenced_operation_ids=referenced_operation_ids,
        )
        operation_id = operation['operationId']
        if operation_id in operation_ids:
            msg = f'Duplicate OpenAPI operationId: {operation_id!r}'
            raise OpenAPIGenerationError(msg)
        operation_ids.add(operation_id)
        path_item[method] = operation
        has_validation = has_validation or bool(route.parameters)

    unknown_operation_ids = referenced_operation_ids - operation_ids
    if unknown_operation_ids:
        unknown = min(unknown_operation_ids)
        msg = f'Unknown OpenAPI operationId {unknown!r} referenced by a response link'
        raise OpenAPIGenerationError(msg)

    schema: dict[str, Any] = {
        'openapi': '3.1.0',
        'info': _info(current_config),
        'paths': paths,
    }
    component_sections = _components(
        registry,
        configured_components=configured_components,
        has_validation=has_validation,
        security_schemes=security_schemes,
    )
    if component_sections:
        schema['components'] = component_sections
    if security:
        schema['security'] = security
    if current_config.servers:
        schema['servers'] = [dict(server) for server in current_config.servers]
    if current_config.tags:
        schema['tags'] = [dict(tag) for tag in current_config.tags]
    if webhooks:
        schema['webhooks'] = webhooks
    return schema
