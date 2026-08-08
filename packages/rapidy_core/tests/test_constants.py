import json

from rapidy_core import constants
from rapidy_core.constants import DEFAULT_JSON_DECODER, DEFAULT_JSON_ENCODER


def test_json_defaults_identity() -> None:
    assert DEFAULT_JSON_ENCODER is json.dumps
    assert DEFAULT_JSON_DECODER is json.loads


def test_json_defaults_roundtrip() -> None:
    assert DEFAULT_JSON_DECODER(DEFAULT_JSON_ENCODER({"a": 1})) == {"a": 1}


def test_server_constants_absent() -> None:
    assert not hasattr(constants, "CLIENT_MAX_SIZE")
    assert not hasattr(constants, "PYDANTIC_IS_V1")
