from __future__ import annotations

from typing import Any

from attrs import define

from rapidy.fields.field_info import RapidyFieldInfo


@define(slots=True)
class Attr:
    """Represents a generic attribute with a name, index, and annotation.

    This class is used as a base for defining attributes with additional information.

    Attributes:
        attribute_name (str): The name of the attribute.
        attribute_idx (int): The index of the attribute.
        attribute_annotation (Any): The annotation (type) of the attribute.
    """

    attribute_name: str
    attribute_idx: int
    attribute_annotation: Any


@define(slots=True)
class DataAttr(Attr):
    """Represents an attribute with associated field information.

    This class extends the `Attr` class by adding `field_info`, which provides
    additional metadata about the field.

    Attributes:
        field_info (RapidyFieldInfo): The metadata associated with the field.
    """

    field_info: RapidyFieldInfo
