from __future__ import annotations

from collections.abc import Iterator

from hypothesis import given, settings
from hypothesis import strategies as st
from rapidy_client import errors

_SECRETS = st.from_regex(r"SECRET_[A-Z0-9]{8,20}", fullmatch=True)


def _subclasses(
    root: type[errors.HttpClientError],
) -> Iterator[type[errors.HttpClientError]]:
    for child in root.__subclasses__():
        yield child
        yield from _subclasses(child)


@settings(max_examples=30, deadline=None)
@given(secret=_SECRETS)
def test_websocket_error_subtree_redacts_messages(secret: str) -> None:
    instances = (
        errors.WSHandshakeError(f"Authorization: {secret}", status=503),
        errors.WSClosedError(
            f"Cookie: {secret}",
            code=1006,
            reason=secret,
        ),
        errors.WSQueueFullError(f"api_key={secret}"),
        errors.MessageValidationError(f"token={secret}"),
    )

    for error in instances:
        assert secret not in str(error)
        assert secret not in repr(error)


def test_recursive_error_inventory_includes_protocol_subtrees() -> None:
    discovered = {
        error_type.__name__ for error_type in _subclasses(errors.HttpClientError)
    }

    assert {
        "ProtocolError",
        "StatusError",
        "WSHandshakeError",
        "WSClosedError",
        "WSMessageTooLargeError",
        "WSQueueFullError",
        "MessageValidationError",
    } <= discovered
