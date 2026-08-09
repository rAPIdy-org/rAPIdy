from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

_FIRST_CONTROL_CODEPOINT = 32
_DELETE_CODEPOINT = 127


def valid_origin(origin: str) -> bool:
    """Return whether a value is a serialized web origin or ``null``."""
    if origin == 'null':
        return True
    if not origin or any(
        character.isspace()
        or ord(character) < _FIRST_CONTROL_CODEPOINT
        or ord(character) == _DELETE_CODEPOINT
        for character in origin
    ):
        return False
    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    )


def normalize_host_pattern(pattern: str) -> str:
    """Validate and normalize one exact or leading-wildcard host pattern."""
    normalized = pattern.rstrip('.').lower()
    if normalized == '*':
        return normalized
    if not normalized or '/' in normalized or '@' in normalized or ':' in normalized:
        msg = f'Invalid trusted host pattern: {pattern!r}'
        raise ValueError(msg)
    if '*' in normalized and (not normalized.startswith('*.') or normalized.count('*') != 1):
        msg = f'Wildcard host patterns must start with "*.": {pattern!r}'
        raise ValueError(msg)
    candidate = normalized.removeprefix('*.')
    try:
        ascii_candidate = candidate.encode('idna').decode('ascii')
    except UnicodeError as exc:
        msg = f'Invalid trusted host pattern: {pattern!r}'
        raise ValueError(msg) from exc
    return f'*.{ascii_candidate}' if normalized.startswith('*.') else ascii_candidate


def parse_host(value: str) -> str | None:
    """Parse and normalize an HTTP authority, ignoring its optional port."""
    if not value or any(character in value for character in '/?#@'):
        return None
    try:
        parsed = urlsplit(f'//{value}')
        host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return None
    if host is None:
        return None
    try:
        return host.rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError:
        return None


def host_is_allowed(host: str, patterns: Iterable[str]) -> bool:
    """Match a normalized host against exact and ``*.example`` patterns."""
    return any(
        pattern in ('*', host) or (pattern.startswith('*.') and host.endswith(pattern[1:]))
        for pattern in patterns
    )
