from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote, urlencode

from rapidy_core.exceptions import RapidyException

__all__ = (
    'DuplicateRouteNameError',
    'InvalidPathParameterError',
    'MissingPathParameterError',
    'RouteNotFoundError',
    'UnexpectedPathParameterError',
    'URLPath',
    'render_path_template',
)


class RouteNotFoundError(RapidyException):
    """Raised when reverse lookup cannot find a named route."""

    message = 'No route named `{name}` is registered.'


class DuplicateRouteNameError(RapidyException):
    """Raised when one name points at more than one route template."""

    message = 'Route name `{name}` is ambiguous; explicit route names must be unique.'


class MissingPathParameterError(RapidyException):
    """Raised when reverse lookup is missing a required path parameter."""

    message = 'Route `{name}` requires path parameter `{parameter}`.'


class UnexpectedPathParameterError(RapidyException):
    """Raised when reverse lookup receives a parameter outside the route template."""

    message = 'Route `{name}` does not declare path parameter `{parameter}`.'


class InvalidPathParameterError(RapidyException):
    """Raised when a rendered value does not match the registered route."""

    message = 'Path parameters do not produce a valid URL for route `{name}`.'


class URLPath(str):
    """Typed application-relative URL path returned by reverse lookup."""

    __slots__ = ()

    def include_query_params(self, **params: object) -> URLPath:
        """Return a copy with percent-encoded query parameters appended."""
        if not params:
            return self
        separator = '&' if '?' in self else '?'
        return URLPath(f'{self}{separator}{urlencode(params, doseq=True)}')


def render_path_template(template: str, values: Mapping[str, object], *, route_name: str) -> URLPath:
    """Render one matcher-compatible path template without exposing raw delimiters."""
    chunks: list[str] = []
    parameter_names: set[str] = set()
    literal_start = 0
    index = 0
    while index < len(template):
        if template[index] != '{':
            index += 1
            continue
        chunks.append(template[literal_start:index])
        end = _find_parameter_end(template, index)
        definition = template[index + 1 : end]
        parameter, separator, expression = definition.partition(':')
        parameter_names.add(parameter)
        if parameter not in values:
            raise MissingPathParameterError(name=route_name, parameter=parameter)
        safe = '/' if separator and expression in {'.*', '.+'} else ''
        rendered = quote(str(values[parameter]), safe=safe)
        if safe and any(part in {'.', '..'} for part in rendered.split('/')):
            raise InvalidPathParameterError(name=route_name)
        chunks.append(rendered)
        index = end + 1
        literal_start = index
    chunks.append(template[literal_start:])

    unexpected = set(values) - parameter_names
    if unexpected:
        raise UnexpectedPathParameterError(name=route_name, parameter=min(unexpected))
    return URLPath(''.join(chunks))


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
    # Templates are validated before registration, so this is unreachable for route records.
    return len(path) - 1
