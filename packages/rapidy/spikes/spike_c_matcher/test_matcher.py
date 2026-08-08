from __future__ import annotations

import httpx
import pytest

from spikes._mini.serve import live_server
from spikes.spike_c_matcher.matcher_proto import MethodNotAllowed, NotFound, UrlMatcher


def _handler() -> None:
    return None


def test_static_route_has_priority_over_dynamic() -> None:
    matcher = UrlMatcher()
    dynamic = object()
    static = object()
    matcher.add_route("GET", "/users/{user_id}", dynamic)
    matcher.add_route("GET", "/users/me", static)
    assert matcher.resolve("GET", "/users/me").terminal is static


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("/users/{user_id}", "/users/42", {"user_id": "42"}),
        (r"/versions/{version:\d+}", "/versions/12", {"version": "12"}),
        ("/files/{tail:.*}", "/files/a/b/c", {"tail": "a/b/c"}),
    ],
)
def test_dynamic_route_forms(pattern: str, path: str, expected: dict[str, str]) -> None:
    matcher = UrlMatcher()
    matcher.add_route("GET", pattern, _handler)
    assert matcher.resolve("GET", path).path_params == expected


def test_auto_head_can_be_disabled() -> None:
    matcher = UrlMatcher()
    matcher.add_route("GET", "/with-head", _handler)
    matcher.add_route("GET", "/without-head", _handler, allow_head=False)
    assert matcher.resolve("HEAD", "/with-head").terminal is _handler
    with pytest.raises(MethodNotAllowed) as error:
        matcher.resolve("HEAD", "/without-head")
    assert error.value.allowed_methods == ("GET",)


def test_404_and_405_allow() -> None:
    matcher = UrlMatcher()
    matcher.add_route("GET", "/items/{item_id}", _handler)
    with pytest.raises(NotFound):
        matcher.resolve("GET", "/missing")
    with pytest.raises(MethodNotAllowed) as error:
        matcher.resolve("POST", "/items/1")
    assert error.value.allowed_methods == ("GET", "HEAD")


@pytest.mark.parametrize("runtime", ["granian", "uvicorn"])
def test_integration_head_405_404(runtime: str) -> None:
    with live_server(runtime, "spikes.spike_c_matcher.app:app") as base_url:
        with httpx.Client(base_url=base_url, timeout=10) as client:
            get_response = client.get("/users/42")
            head_response = client.head("/users/42")
            method_response = client.post("/users/42")
            missing_response = client.get("/missing")
            static_response = client.get("/users/me")
    assert get_response.status_code == 200 and get_response.content == b"user:42"
    assert head_response.status_code == 200 and head_response.content == b""
    assert head_response.headers["content-length"] == str(len(b"user:42"))
    assert method_response.status_code == 405
    assert method_response.headers["allow"] == "GET, HEAD"
    assert missing_response.status_code == 404
    assert static_response.content == b"static"
