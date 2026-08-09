from __future__ import annotations

import re
from collections.abc import Callable
from concurrent.futures import Executor
from functools import wraps
from http import HTTPStatus
from typing import Any, cast, overload, TypeVar
from urllib.parse import quote, quote_from_bytes

from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.encoders import CustomEncoder, Exclude, Include  # noqa: TC002 - runtime annotations
from rapidy_core.enums import Charset, ContentType

from .compression import CompressionAlgorithm, CompressionMiddleware, GZipMiddleware, MissingBrotliDependencyError
from .cors import CORSMiddleware
from .hosts import HTTPSRedirectMiddleware, TrustedHostMiddleware
from .proxy_headers import ProxyHeaderMode, ProxyHeadersMiddleware
from .request_id import get_request_context, get_request_id, RequestContext, RequestIDMiddleware
from rapidy.exceptions import HTTPNotFound, HTTPPermanentRedirect
from rapidy.middlewares.runner import MiddlewareAttrData
from rapidy.request import Request
from rapidy.typedefs import CallNext, JSONEncoder, Middleware, UNSET, UnsetType

__all__ = (
    'CORSMiddleware',
    'CompressionAlgorithm',
    'CompressionMiddleware',
    'GZipMiddleware',
    'HTTPSRedirectMiddleware',
    'MissingBrotliDependencyError',
    'ProxyHeaderMode',
    'ProxyHeadersMiddleware',
    'RequestContext',
    'RequestIDMiddleware',
    'TrustedHostMiddleware',
    'get_request_context',
    'get_request_id',
    'middleware',
    'normalize_path_middleware',
)

TMiddleware = TypeVar('TMiddleware', bound=Middleware)


@overload
def middleware(middleware: TMiddleware) -> TMiddleware: ...  # noqa: UP047


@overload
def middleware(
    *,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: type[Any] | UnsetType | None = UNSET,
    response_content_type: str | ContentType | None = None,
    response_charset: str | Charset = Charset.utf8,
    response_zlib_executor: Executor | None = None,
    response_zlib_executor_size: int | None = None,
    response_include_fields: Include | None = None,
    response_exclude_fields: Exclude | None = None,
    response_by_alias: bool = True,
    response_exclude_unset: bool = False,
    response_exclude_defaults: bool = False,
    response_exclude_none: bool = False,
    response_custom_encoder: CustomEncoder | None = None,
    response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> Callable[[Any], TMiddleware]: ...


def middleware(  # noqa: UP047
    middleware: TMiddleware | None = None,
    *,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: type[Any] | UnsetType | None = UNSET,
    response_content_type: str | ContentType | None = None,
    response_charset: str | Charset = Charset.utf8,
    response_zlib_executor: Executor | None = None,
    response_zlib_executor_size: int | None = None,
    response_include_fields: Include | None = None,
    response_exclude_fields: Exclude | None = None,
    response_by_alias: bool = True,
    response_exclude_unset: bool = False,
    response_exclude_defaults: bool = False,
    response_exclude_none: bool = False,
    response_custom_encoder: CustomEncoder | None = None,
    response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> TMiddleware | Callable[[Any], TMiddleware]:
    """Mark a middleware and attach its extraction and response policy."""
    middleware_attr_data = MiddlewareAttrData(
        status_code=status_code,
        response_validate=response_validate,
        response_type=response_type,
        response_content_type=response_content_type,
        response_charset=response_charset,
        response_zlib_executor=response_zlib_executor,
        response_zlib_executor_size=response_zlib_executor_size,
        response_include_fields=response_include_fields,
        response_exclude_fields=response_exclude_fields,
        response_by_alias=response_by_alias,
        response_exclude_unset=response_exclude_unset,
        response_exclude_defaults=response_exclude_defaults,
        response_exclude_none=response_exclude_none,
        response_custom_encoder=response_custom_encoder,
        response_json_encoder=response_json_encoder,
    )
    if middleware is None:

        def inner_middleware(current_middleware: TMiddleware) -> TMiddleware:
            return _create_rapidy_middleware(current_middleware, middleware_attr_data)

        return inner_middleware
    return _create_rapidy_middleware(middleware, middleware_attr_data)


def _create_rapidy_middleware(  # noqa: UP047
    current_middleware: TMiddleware,
    middleware_attr_data: MiddlewareAttrData,
) -> TMiddleware:
    generic_middleware = cast('Any', current_middleware)
    generic_middleware.__rapidy_middleware__ = True
    generic_middleware.__attr_data__ = middleware_attr_data

    @wraps(current_middleware)
    async def impl(request: Request, call_next: CallNext, **kwargs: Any) -> Any:
        return await current_middleware(request, call_next, **kwargs)

    return cast('TMiddleware', impl)


def get_middleware_attr_data(current_middleware: Middleware) -> MiddlewareAttrData:
    """Return policy attached by ``@middleware``."""
    return cast('MiddlewareAttrData', cast('Any', current_middleware).__attr_data__)


def is_rapidy_middleware(current_middleware: Middleware) -> bool:
    """Return whether a middleware uses the native rAPIdy marker."""
    return getattr(current_middleware, '__rapidy_middleware__', False) is True


def normalize_path_middleware(  # noqa: C901
    *,
    append_slash: bool = True,
    remove_slash: bool = False,
    merge_slashes: bool = True,
) -> Middleware:
    """Redirect a 404 to the first resolvable normalized path."""
    if append_slash and remove_slash:
        msg = 'Cannot both remove and append slash'
        raise ValueError(msg)

    @middleware
    async def normalize_path(request: Request, call_next: CallNext) -> Any:
        try:
            return await call_next(request)
        except HTTPNotFound:
            path = str(request.scope.get('_rapidy_mount_path', request.path))
            paths_to_check: list[str] = []
            if merge_slashes:
                paths_to_check.append(re.sub('/+', '/', path))
            if append_slash and not path.endswith('/'):
                paths_to_check.append(f'{path}/')
            if remove_slash and path.endswith('/'):
                paths_to_check.append(path[:-1])
            if merge_slashes and append_slash and not path.endswith('/'):
                paths_to_check.append(re.sub('/+', '/', f'{path}/'))
            if merge_slashes and remove_slash and path.endswith('/'):
                paths_to_check.append(re.sub('/+', '/', path)[:-1])

            for candidate in dict.fromkeys(paths_to_check):
                if (
                    candidate != path
                    and candidate.startswith('/')
                    and not candidate.startswith('//')
                    and request.app._can_resolve(request.method, candidate)  # noqa: SLF001
                ):
                    prefix = str(request.scope.get('_rapidy_mount_prefix', ''))
                    query_string = quote_from_bytes(
                        cast('bytes', request.scope.get('query_string', b'')),
                        safe="!$&'()*+,-./:;=?@_~%",
                    )
                    query_suffix = f'?{query_string}' if query_string else ''
                    encoded_candidate = quote(candidate, safe="/%:@!$&'()*+,;=-._~")
                    location = f'{prefix}{encoded_candidate}{query_suffix}'
                    raise HTTPPermanentRedirect(location) from None
            raise

    return normalize_path
