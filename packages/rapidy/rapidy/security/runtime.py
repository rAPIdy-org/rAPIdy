from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from typing import cast

from rapidy.exceptions import HTTPForbidden, HTTPUnauthorized
from rapidy.request import Request
from rapidy.security.config import Guard, SecurityConfig, SecurityRequirements
from rapidy.security.models import ANONYMOUS_IDENTITY, AuthCredentials, SecurityIdentity
from rapidy.security.schemes import AuthenticationError, SecurityScheme

__all__ = ('authorize_request',)

_AUTH_CACHE_KEY = '_rapidy_security_auth_cache'
_AUTH_FAILED = object()
_IDENTITY_KEY = '_rapidy_security_identity'


async def _authenticate(
    request: Request,
    scheme: SecurityScheme,
) -> SecurityIdentity | None:
    cache = cast(
        'dict[str, SecurityIdentity | object | None]',
        request.state.setdefault(_AUTH_CACHE_KEY, {}),
    )
    cached = cache.get(scheme.name, ...)
    if cached is _AUTH_FAILED:
        raise AuthenticationError
    if cached is not ...:
        return cast('SecurityIdentity | None', cached)
    try:
        identity = await scheme.authenticate(request)
    except AuthenticationError:
        cache[scheme.name] = _AUTH_FAILED
        raise
    cache[scheme.name] = identity
    return identity


def _merge_identities(identities: Sequence[SecurityIdentity]) -> SecurityIdentity:
    primary = identities[0]
    scopes = frozenset(scope for identity in identities for scope in identity.auth.scopes)
    schemes = tuple(dict.fromkeys(scheme for identity in identities for scheme in identity.auth.schemes))
    return SecurityIdentity(user=primary.user, auth=AuthCredentials(scopes=scopes, schemes=schemes))


def _unauthorized(schemes: Mapping[str, SecurityScheme]) -> HTTPUnauthorized:
    challenges = tuple(dict.fromkeys(scheme.challenge for scheme in schemes.values() if scheme.challenge))
    headers = {'WWW-Authenticate': ', '.join(challenges)} if challenges else None
    return HTTPUnauthorized(headers=headers)


async def _run_guards(request: Request, guards: Sequence[Guard]) -> None:
    for guard in guards:
        result = guard(request)
        if inspect.isawaitable(result):
            result = await result
        if result is False:
            raise HTTPForbidden


async def authorize_request(
    request: Request,
    *,
    schemes: Mapping[str, SecurityScheme],
    requirements: SecurityRequirements,
    guards: Sequence[Guard] = (),
) -> SecurityIdentity:
    """Enforce OpenAPI-shaped security requirements and cumulative route guards."""
    request.state.setdefault(_IDENTITY_KEY, ANONYMOUS_IDENTITY)
    normalized_requirements = SecurityConfig.normalize_requirements(requirements)
    if normalized_requirements:
        request.state[_IDENTITY_KEY] = await _resolve_requirements(request, schemes, normalized_requirements)

    await _run_guards(request, guards)
    return cast('SecurityIdentity', request.state[_IDENTITY_KEY])


async def _resolve_requirements(
    request: Request,
    schemes: Mapping[str, SecurityScheme],
    requirements: SecurityRequirements,
) -> SecurityIdentity:
    authenticated_but_forbidden = False
    invalid_credentials = False
    ordered = sorted(requirements, key=bool, reverse=True)
    for requirement in ordered:
        if not requirement:
            if not invalid_credentials:
                return ANONYMOUS_IDENTITY
            continue
        identities: list[SecurityIdentity] = []
        for scheme_name, required_scopes in requirement.items():
            try:
                scheme = schemes[scheme_name]
            except KeyError as exc:
                msg = f'Unknown runtime security scheme: {scheme_name!r}'
                raise RuntimeError(msg) from exc
            try:
                identity = await _authenticate(request, scheme)
            except AuthenticationError:
                invalid_credentials = True
                break
            if identity is None:
                break
            if not identity.auth.allows(*required_scopes):
                authenticated_but_forbidden = True
                break
            identities.append(identity)
        else:
            return _merge_identities(identities)

    if authenticated_but_forbidden:
        raise HTTPForbidden
    referenced_schemes = {
        name: schemes[name]
        for requirement in requirements
        for name in requirement
        if name in schemes
    }
    raise _unauthorized(referenced_schemes)
