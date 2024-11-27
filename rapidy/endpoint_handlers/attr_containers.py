from typing import Any

from attrs import define

from rapidy.fields.field_info import RapidyFieldInfo


@define(slots=True)
class Attr:
    attribute_name: str
    attribute_idx: int
    attribute_annotation: Any


@define(slots=True)
class DataAttr(Attr):
    field_info: RapidyFieldInfo
