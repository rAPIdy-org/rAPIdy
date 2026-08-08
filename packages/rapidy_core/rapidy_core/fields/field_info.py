from __future__ import annotations

import warnings
from copy import deepcopy
from typing import Any

from pydantic.fields import FieldInfo

from rapidy_core.annotation_checkers import is_annotated, is_not_none_and_unset
from rapidy_core.typedefs import UNSET, Deprecated, NoArgAnyCallable, Undefined, Unset

__all__ = ("RapidyFieldInfo", "copy_field_info")


class RapidyFieldInfo(FieldInfo):  # type: ignore[misc]  # pydantic supports this despite its final marker
    """Extended pydantic field metadata used by rAPIdy parameter markers."""

    name: str
    annotation: Any
    can_default: bool = True
    need_validate: bool

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | Unset = UNSET,
        annotation: Any | None | Unset = UNSET,
        alias: str | None | Unset = UNSET,
        alias_priority: int | None | Unset = UNSET,
        validation_alias: str | None | Unset = UNSET,
        serialization_alias: str | None | Unset = UNSET,
        title: str | None | Unset = UNSET,
        description: str | None | Unset = UNSET,
        gt: float | None | Unset = UNSET,
        ge: float | None | Unset = UNSET,
        lt: float | None | Unset = UNSET,
        le: float | None | Unset = UNSET,
        min_length: int | None | Unset = UNSET,
        max_length: int | None | Unset = UNSET,
        pattern: str | None | Unset = UNSET,
        discriminator: str | None | Unset = UNSET,
        strict: bool | None | Unset = UNSET,
        multiple_of: float | None | Unset = UNSET,
        allow_inf_nan: bool | None | Unset = UNSET,
        max_digits: int | None | Unset = UNSET,
        decimal_places: int | None | Unset = UNSET,
        deprecated: Deprecated | str | bool | None | Unset = UNSET,
        examples: list[Any] | None | Unset = UNSET,
        json_schema_extra: dict[str, Any] | None | Unset = UNSET,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        json_schema_extra = json_schema_extra if json_schema_extra is not UNSET else {}
        self.need_validate = validate
        regex = extra.pop("regex", None)

        kwargs: dict[str, Any] = {
            "default": default,
            "default_factory": default_factory,
            "alias": alias,
            "title": title,
            "description": description,
            "gt": gt,
            "ge": ge,
            "lt": lt,
            "le": le,
            "min_length": min_length,
            "max_length": max_length,
            "discriminator": discriminator,
            "multiple_of": multiple_of,
            "allow_inf_nan": allow_inf_nan,
            "max_digits": max_digits,
            "decimal_places": decimal_places,
            **extra,
        }

        if examples is not None:
            kwargs["examples"] = examples

        current_json_schema_extra = json_schema_extra or extra
        kwargs.update(
            {
                "annotation": annotation,
                "alias_priority": alias_priority,
                "validation_alias": validation_alias,
                "serialization_alias": serialization_alias,
                "strict": strict,
                "json_schema_extra": current_json_schema_extra,
            },
        )
        kwargs["pattern"] = self._get_pattern(pattern=pattern, regex=regex)
        kwargs["deprecated"] = deprecated

        super().__init__(
            **{key: value for key, value in kwargs.items() if value is not UNSET}
        )

    def _get_pattern(self, pattern: str | None | Unset, regex: str | None) -> Any:
        if is_not_none_and_unset(pattern):
            return pattern
        if is_not_none_and_unset(regex):
            warnings.warn(
                "`regex` has been deprecated, please use `pattern` instead",
                category=DeprecationWarning,
                stacklevel=4,
            )
            return regex
        return UNSET


def copy_field_info(*, field_info: RapidyFieldInfo, annotation: Any) -> RapidyFieldInfo:
    """Copy field metadata and merge metadata carried by ``Annotated``."""
    # FIXME:
    #  If the desired data type is of type `Union` (pydantic.UUID4, ...), the metadata will be assembled according
    #  to the parameter definition.
    #  Example: `data: Annotated[UUID4, Body(regex='some')`
    #  >> field_info.metadata = [UuidVersion(uuid_version=4), _PydanticGeneralMetadata(pattern=re.compile('test'))]
    #  Example: `data UUID4 = Body(regex='some')`
    #  >> field_info.metadata = [_PydanticGeneralMetadata(pattern=re.compile('some'))]
    #  Note: It's not affecting anything yet, but it's something to look out for.
    copied_param_field_info = deepcopy(field_info)

    if is_annotated(annotation):
        merged_field_info = type(field_info).from_annotation(annotation)
        copied_param_field_info.metadata = merged_field_info.metadata
        copied_param_field_info.annotation = merged_field_info.annotation

    return copied_param_field_info
