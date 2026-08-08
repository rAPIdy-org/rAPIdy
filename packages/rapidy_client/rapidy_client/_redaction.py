from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DENY_HEADERS: frozenset[str] = frozenset(
    {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key"}
)
DENY_QUERY: frozenset[str] = frozenset({"token", "api_key", "signature"})
REDACTED = "<redacted>"
MAX_VALUE_LEN = 256
CROP_SUFFIX = "…(cropped)"


class Redactor:
    __slots__ = ("_deny_headers", "_deny_query", "_max_value_len")

    def __init__(
        self,
        *,
        extra_headers: Iterable[str] = (),
        extra_query: Iterable[str] = (),
        max_value_len: int = MAX_VALUE_LEN,
    ) -> None:
        self._deny_headers = DENY_HEADERS | frozenset(
            header.casefold() for header in extra_headers
        )
        self._deny_query = DENY_QUERY | frozenset(
            query.casefold() for query in extra_query
        )
        self._max_value_len = max_value_len

    def redact_header_value(self, name: str, value: str) -> str:
        if name.casefold() in self._deny_headers:
            return REDACTED
        return self.crop(value)

    def redact_headers(self, items: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
        return [(name, self.redact_header_value(name, value)) for name, value in items]

    def redact_query_string(self, query_string: str) -> str:
        pairs = parse_qsl(query_string, keep_blank_values=True)
        redacted = [
            (
                key,
                REDACTED if key.casefold() in self._deny_query else self.crop(value),
            )
            for key, value in pairs
        ]
        return urlencode(redacted)

    def redact_url_str(self, url_str: str) -> str:
        parts = urlsplit(url_str)
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                self.redact_query_string(parts.query),
                parts.fragment,
            )
        )

    def redact_text(self, text: str) -> str:
        result = text
        for name in self._deny_headers:
            escaped = re.escape(name)
            if name in {"authorization", "proxy-authorization"}:
                value = r"[^\s,;]+(?:\s+[^\s,;]+)?"
            else:
                value = r"[^\s,;]+"
            result = re.sub(
                rf"(?i)({escaped}\s*[:=]\s*)({value})",
                rf"\g<1>{REDACTED}",
                result,
            )
        for key in self._deny_query:
            result = re.sub(
                rf"(?i)([?&]{re.escape(key)}=)([^&\s]+)",
                rf"\g<1>{REDACTED}",
                result,
            )
        return result

    def crop(self, value: str) -> str:
        if len(value) <= self._max_value_len:
            return value
        return value[: self._max_value_len] + CROP_SUFFIX

    def extend(
        self,
        *,
        headers: Iterable[str] = (),
        query: Iterable[str] = (),
    ) -> Redactor:
        return Redactor(
            extra_headers=self._deny_headers
            | frozenset(header.casefold() for header in headers),
            extra_query=self._deny_query | frozenset(key.casefold() for key in query),
            max_value_len=self._max_value_len,
        )


DEFAULT_REDACTOR = Redactor()

__all__ = (
    "CROP_SUFFIX",
    "DEFAULT_REDACTOR",
    "DENY_HEADERS",
    "DENY_QUERY",
    "MAX_VALUE_LEN",
    "REDACTED",
    "Redactor",
)
