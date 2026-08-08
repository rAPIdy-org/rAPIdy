from urllib.parse import parse_qsl

from rapidy_client._redaction import (
    CROP_SUFFIX,
    DEFAULT_REDACTOR,
    DENY_HEADERS,
    DENY_QUERY,
    MAX_VALUE_LEN,
    REDACTED,
)


def test_deny_lists_exact() -> None:
    assert DENY_HEADERS == {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    }
    assert DENY_QUERY == {"token", "api_key", "signature"}


def test_redact_header_value_masks_denylist() -> None:
    assert (
        DEFAULT_REDACTOR.redact_header_value("Authorization", "Bearer s3cret")
        == REDACTED
    )
    assert DEFAULT_REDACTOR.redact_header_value("authorization", "s3cret") == REDACTED


def test_redact_header_value_passes_allowed_and_crops() -> None:
    assert DEFAULT_REDACTOR.redact_header_value("X-Trace", "abc") == "abc"
    value = DEFAULT_REDACTOR.redact_header_value("X-Trace", "x" * (MAX_VALUE_LEN + 1))
    assert value.endswith(CROP_SUFFIX)


def test_redact_headers_preserves_multivalue() -> None:
    items = [("Set-Cookie", "one=x"), ("Set-Cookie", "two=y")]
    assert DEFAULT_REDACTOR.redact_headers(items) == [
        ("Set-Cookie", REDACTED),
        ("Set-Cookie", REDACTED),
    ]


def test_redact_query_string_masks_secret_keys() -> None:
    result = DEFAULT_REDACTOR.redact_query_string("token=x&a=1&api_key=y&signature=z")
    values = dict(parse_qsl(result))
    assert values == {
        "token": REDACTED,
        "a": "1",
        "api_key": REDACTED,
        "signature": REDACTED,
    }


def test_redact_url_str_reassembles_nonsecret() -> None:
    result = DEFAULT_REDACTOR.redact_url_str("https://h/p?token=x&a=1")
    assert "x" not in result
    assert result.startswith("https://h/p?")
    assert "a=1" in result


def test_redact_text_scrubs_header_and_query() -> None:
    result = DEFAULT_REDACTOR.redact_text(
        "failed Authorization: Bearer S; url ?token=T"
    )
    assert "Bearer S" not in result
    assert "token=T" not in result
    assert REDACTED in result


def test_crop_threshold() -> None:
    exact = "x" * MAX_VALUE_LEN
    assert DEFAULT_REDACTOR.crop(exact) == exact
    assert DEFAULT_REDACTOR.crop(exact + "x").endswith(CROP_SUFFIX)


def test_extend_adds_per_upstream_keys() -> None:
    extended = DEFAULT_REDACTOR.extend(query={"sid"})
    assert "x" not in extended.redact_query_string("sid=x")
    assert DEFAULT_REDACTOR.redact_query_string("sid=x") == "sid=x"
