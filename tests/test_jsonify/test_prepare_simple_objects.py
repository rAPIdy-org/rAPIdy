import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel

from rapidy.encoders import jsonify

test_str = 'test'
test_int = 1


class _TestEnum(Enum):
    test = test_str


class _TestBaseModel(BaseModel):
    test_str: str
    test_int: int


@dataclass
class _TestDataclass:
    test_str: str
    test_int: int


def test_decimal() -> None:
    d_str = '1.000000001'
    assert jsonify(Decimal(d_str)) == d_str


def test_enum() -> None:
    assert jsonify(_TestEnum.test) == test_str


def test_uuid4() -> None:
    test_uuid = uuid4()
    test_val = str(test_uuid)
    assert jsonify(test_uuid) == test_val


def test_datetime_date() -> None:
    test_date = datetime.date(2020, 1, 1)
    test_val = '2020-01-01'
    assert jsonify(test_date) == test_val


def test_datetime_datetime() -> None:
    test_date = datetime.datetime(2020, 1, 1, 1, 1, 1)
    test_val = '2020-01-01T01:01:01'
    assert jsonify(test_date) == test_val


def test_bytes() -> None:
    assert jsonify(test_str.encode()) == test_str


def test_base_model() -> None:
    model = _TestBaseModel(test_str=test_str, test_int=test_int)
    assert jsonify(model) == {'test_str': test_str, 'test_int': test_int}


def test_dataclass() -> None:
    model = _TestDataclass(test_str=test_str, test_int=test_int)
    assert jsonify(model) == {'test_str': test_str, 'test_int': test_int}
