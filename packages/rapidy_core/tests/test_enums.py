from rapidy_core import enums
from rapidy_core.enums import (
    Charset,
    ContentType,
    HeaderName,
    HTTPMethod,
    HTTPRequestParamType,
)


def test_http_method_renamed_from_method_name() -> None:
    assert [member.value for member in HTTPMethod] == [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
        "*",
    ]
    assert not hasattr(enums, "MethodName")


def test_http_method_is_str_subclass() -> None:
    assert isinstance(HTTPMethod.post, str)
    assert HTTPMethod.post == "POST"


def test_string_enum_values() -> None:
    assert ContentType.json == "application/json"
    assert ContentType.any == "*/*"
    assert str(ContentType.json) == "application/json"
    assert repr(ContentType.json) == "application/json"
    assert Charset.utf8 == "utf-8"
    assert Charset.utf16 == "utf-16"
    assert Charset.utf32 == "utf-32"


def test_header_name_values() -> None:
    assert HeaderName.authorization == "Authorization"
    assert HeaderName.content_type == "Content-Type"
    assert HeaderName.set_cookie == "Set-Cookie"
    assert HeaderName.retry_after == "Retry-After"
    assert HeaderName.user_agent == "User-Agent"


def test_http_request_param_type_values() -> None:
    assert [member.value for member in HTTPRequestParamType] == [
        "path",
        "query",
        "header",
        "cookie",
        "body",
    ]


def test_all_exports() -> None:
    assert set(enums.__all__) == {
        "HTTPMethod",
        "ContentType",
        "HeaderName",
        "Charset",
        "HTTPRequestParamType",
    }
