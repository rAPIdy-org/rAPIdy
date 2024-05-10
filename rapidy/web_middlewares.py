from typing import TypeVar

from aiohttp.web_middlewares import middleware as aiohttp_middleware, normalize_path_middleware

__all__ = (
    'middleware',
    'normalize_path_middleware',
)

from rapidy.typedefs import Middleware

TMiddleware = TypeVar('TMiddleware')


def middleware(middleware: TMiddleware) -> TMiddleware:  # noqa: WPS442
    aiohttp_middleware(middleware)
    middleware.__rapidy_middleware__ = True  # type: ignore[attr-defined]
    return middleware


def is_aiohttp_new_style_middleware(middleware: Middleware) -> bool:  # noqa: WPS442
    return getattr(middleware, '__middleware_version__', 0) == 1


def is_rapidy_middleware(middleware: Middleware) -> bool:  # noqa: WPS442
    return getattr(middleware, '__rapidy_middleware__', False) is True
