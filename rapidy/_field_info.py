from functools import cached_property
from typing import Any, Optional

from pydantic.fields import FieldInfo as PydanticFieldInfo

from rapidy._constants import PYDANTIC_V1
from rapidy.typedefs import NoArgAnyCallable, Undefined


class RapidyFieldInfo(PydanticFieldInfo):
    attribute_name: str
    annotation: Any
    can_default: bool

    def __init__(
            self,
            default: Any = Undefined,
            *,
            default_factory: Optional[NoArgAnyCallable] = None,
            validate: bool = True,
            **field_info_kwargs: Any,
    ) -> None:
        PydanticFieldInfo.__init__(
            self,
            default=default,
            default_factory=default_factory,
            **field_info_kwargs,
        )
        if PYDANTIC_V1:
            self._validate()  # check specify both default and default_factory

        self._need_validate = validate

    def set_annotation(self, annotation: Any) -> None:  # noqa: WPS615
        self.annotation = annotation

    @cached_property
    def need_validate(self) -> bool:  # noqa: WPS615
        return self._need_validate

    def set_attribute_name(self, attribute_name: str) -> None:  # noqa: WPS615
        self.attribute_name = attribute_name
