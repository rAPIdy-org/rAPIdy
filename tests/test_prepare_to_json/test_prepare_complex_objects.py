import datetime
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from rapidy.encoders import simplify_data

test_str = 'test'
test_int = 1
test_decimal_str = '1.0000001'
test_decimal = Decimal(test_decimal_str)
test_datetime = datetime.datetime(2020, 1, 1, 1, 1, 1)
test_datetime_str_val = '2020-01-01T01:01:01'


def get_fake_now_datetime() -> datetime.datetime:
    return test_datetime


class _TestEnum(Enum):
    test = test_str


iterable_objects = (test_int, test_str, _TestEnum.test, test_decimal, test_datetime)
prepared_iterable_objects = [1, test_str, _TestEnum.test.value, test_decimal_str, test_datetime_str_val]


class _TestBaseModel(BaseModel):
    test_str: str = test_str
    test_enum: _TestEnum = _TestEnum.test
    test_int: int = test_int
    test_decimal: Decimal = test_decimal
    test_datetime: datetime.datetime = Field(default_factory=get_fake_now_datetime)


@dataclass
class _TestDataclass:
    test_str: str = test_str
    test_enum: _TestEnum = _TestEnum.test
    test_int: int = test_int
    test_decimal: Decimal = test_decimal
    test_datetime: datetime.datetime = field(default_factory=get_fake_now_datetime)


obj_to_prepare = {
    'test_int': test_int,
    'test_str': test_str,
    'test_enum': _TestEnum.test,
    'test_decimal': test_decimal,
    'test_datetime': test_datetime,
    'test_list': [*iterable_objects],
    'test_set': {*iterable_objects},
    'test_frozenset': frozenset(iterable_objects),
    'test_deque': deque(iterable_objects),
    'test_base_model': _TestBaseModel(),
    'test_dataclass': _TestDataclass(),
    'test_list_complex': [_TestBaseModel(), _TestDataclass()],
}

expected_prepared_obj = {
    'test_int': 1,
    'test_str': test_str,
    'test_enum': _TestEnum.test.value,
    'test_decimal': test_decimal_str,
    'test_datetime': test_datetime_str_val,
    'test_base_model': {
        'test_int': test_int,
        'test_str': test_str,
        'test_datetime': test_datetime_str_val,
        'test_decimal': test_decimal_str,
        'test_enum': _TestEnum.test.value,
    },
    'test_dataclass': {
        'test_int': test_int,
        'test_str': test_str,
        'test_datetime': test_datetime_str_val,
        'test_decimal': test_decimal_str,
        'test_enum': _TestEnum.test.value,
    },
    'test_list_complex': [
        {
            'test_int': test_int,
            'test_str': test_str,
            'test_datetime': test_datetime_str_val,
            'test_decimal': test_decimal_str,
            'test_enum': _TestEnum.test.value,
        },
        {
            'test_int': test_int,
            'test_str': test_str,
            'test_datetime': test_datetime_str_val,
            'test_decimal': test_decimal_str,
            'test_enum': _TestEnum.test.value,
        },
    ],
}


def test_complex() -> None:
    prepared_obj = simplify_data(obj_to_prepare)

    prepared_list = prepared_obj.pop('test_list')
    prepared_set = prepared_obj.pop('test_set')
    prepared_frozenset = prepared_obj.pop('test_frozenset')
    prepared_deque = prepared_obj.pop('test_deque')
    assert (
        set(prepared_list) ==
        set(prepared_set) ==
        set(prepared_frozenset) ==
        set(prepared_deque) ==
        set(prepared_iterable_objects)
    )

    assert prepared_obj == expected_prepared_obj
