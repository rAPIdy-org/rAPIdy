from typing import Final

from rapidy.encoders import simplify_data

DEFAULT: Final[str] = 'test'


def test_dict_include() -> None:
    test_dict = {DEFAULT: DEFAULT, 'excluded_field_1': DEFAULT, 'excluded_field_2': DEFAULT}
    assert simplify_data(test_dict, include={DEFAULT}) == {DEFAULT: DEFAULT}


def test_dict_exclude_none() -> None:
    test_dict = {'test_null': None, DEFAULT: DEFAULT}
    assert simplify_data(test_dict, exclude_none=True) == {DEFAULT: DEFAULT}


def test_dict_exclude() -> None:
    test_dict = {'test_exclude': DEFAULT, DEFAULT: DEFAULT}
    assert simplify_data(test_dict, exclude={'test_exclude'}) == {DEFAULT: DEFAULT}
