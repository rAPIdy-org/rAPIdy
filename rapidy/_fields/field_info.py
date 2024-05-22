from abc import ABC
from typing import Any, Optional

from pydantic.fields import FieldInfo as FieldInfo

from rapidy.constants import PYDANTIC_V1
from rapidy.request._enums import HTTPRequestParamType
from rapidy.typedefs import NoArgAnyCallable, Undefined


class ParamFieldInfo(FieldInfo, ABC):
    annotation: Any
    http_request_param_type: HTTPRequestParamType
    extract_all: bool
    can_default: bool

    def __init__(
            self,
            default: Any = Undefined,
            *,
            default_factory: Optional[NoArgAnyCallable] = None,
            validate: bool = True,
            **field_info_kwargs: Any,
    ) -> None:
        FieldInfo.__init__(
            self,
            default=default,
            default_factory=default_factory,
            **field_info_kwargs,
        )
        if PYDANTIC_V1:
            self._validate()  # check specify both default and default_factory

        self._validate_data = validate

    def prepare(self, annotation: Any) -> None:
        self.annotation = annotation

    @property
    def validate(self) -> bool:
        return self._validate_data
