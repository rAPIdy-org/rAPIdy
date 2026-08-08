import abc
import inspect

from rapidy_core.exceptions import RapidyException


class _Error(RapidyException):
    message = "boom"


class _FormattedError(RapidyException):
    message = "x={val}"


def test_message_wrapped_with_border() -> None:
    message = str(_Error())
    assert "boom" in message
    assert "-" * 30 in message


def test_explicit_message_overrides_class_message() -> None:
    assert "custom" in str(_Error("custom"))


def test_format_fields_substituted() -> None:
    assert "x=7" in str(_FormattedError(val="7"))


def test_no_create_no_handler_partial() -> None:
    assert not hasattr(RapidyException, "create")
    module = inspect.getmodule(RapidyException)
    assert module is not None
    assert "HandlerPartial" not in inspect.getsource(module)


def test_is_abc_subclass() -> None:
    assert issubclass(RapidyException, Exception)
    assert isinstance(RapidyException, abc.ABCMeta)
