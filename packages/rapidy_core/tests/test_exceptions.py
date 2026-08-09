import abc
import inspect

from rapidy_core.exceptions import RapidyException


class _Error(RapidyException):
    message = "boom"


class _FormattedError(RapidyException):
    message = "x={val}"


def test_message_is_stable_log_friendly_text() -> None:
    error = _Error()
    assert str(error) == "boom"
    assert error.args == ("boom",)


def test_explicit_message_overrides_class_message() -> None:
    assert str(_Error("custom")) == "custom"


def test_format_fields_substituted() -> None:
    assert str(_FormattedError(val="7")) == "x=7"


def test_no_create_no_handler_partial() -> None:
    assert not hasattr(RapidyException, "create")
    module = inspect.getmodule(RapidyException)
    assert module is not None
    assert "HandlerPartial" not in inspect.getsource(module)


def test_is_abc_subclass() -> None:
    assert issubclass(RapidyException, Exception)
    assert isinstance(RapidyException, abc.ABCMeta)
