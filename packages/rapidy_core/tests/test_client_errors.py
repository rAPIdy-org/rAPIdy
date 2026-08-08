import inspect

from rapidy_core import client_errors
from rapidy_core.client_errors import (
    ClientError,
    RequiredFieldIsMissingError,
    normalize_errors,
    regenerate_error_with_loc,
)


def test_required_field_is_missing_attrs() -> None:
    error = RequiredFieldIsMissingError()
    assert error.type == "missing"
    assert error.msg_template == "Field required"


def test_get_error_info_shape() -> None:
    info = RequiredFieldIsMissingError().get_error_info(("body", "name"))
    assert info["loc"] == ("body", "name")
    assert info["type"] == "missing"
    assert info["msg"] == "Field required"


def test_get_error_info_str_loc_normalized() -> None:
    assert RequiredFieldIsMissingError().get_error_info("name")["loc"] == ("name",)


def test_regenerate_error_with_loc_prefixes() -> None:
    errors = [{"loc": ("x",), "msg": "m", "type": "t"}]
    assert regenerate_error_with_loc(errors=errors, loc=("body",)) == [
        {"loc": ("body", "x"), "msg": "m", "type": "t"},
    ]


def test_normalize_errors_pops_useless_keys_list() -> None:
    result = normalize_errors([{"url": "u", "input": 1, "msg": "m"}])
    assert result == [{"msg": "m"}]


def test_normalize_errors_single_wraps_and_pops() -> None:
    assert normalize_errors({"input": 1, "msg": "m"}) == [{"msg": "m"}]


def test_normalize_errors_keeps_keys_when_flag_false() -> None:
    values = [{"url": "u", "input": 1, "msg": "m"}]
    assert normalize_errors(values, pop_useless_keys=False) == values
    value = {"input": 1, "msg": "m"}
    assert normalize_errors(value, pop_useless_keys=False) == [value]


def test_symbols_importable() -> None:
    assert ClientError is not None
    assert RequiredFieldIsMissingError is not None
    assert normalize_errors is not None
    assert regenerate_error_with_loc is not None


def test_no_pydantic_v1_branch() -> None:
    assert "PYDANTIC_IS_V1" not in inspect.getsource(client_errors)
