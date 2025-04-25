from __future__ import annotations

import warnings
from copy import deepcopy
from typing import Any, Dict, List

from pydantic.fields import FieldInfo

from rapidy.annotation_checkers import is_annotated, is_not_none_and_unset
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import Deprecated, NoArgAnyCallable, Undefined, Unset, UnsetType
from rapidy.version import PYDANTIC_VERSION_TUPLE


class RapidyFieldInfo(FieldInfo):
    """
    Extended Pydantic FieldInfo with additional functionality for Rapidy parameters.

    Attributes:
        name (str): The name of the field.
        annotation (Any): The field's type annotation.
        can_default (bool): Whether the field can have a default value. Defaults to True.
    """

    name: str
    annotation: Any
    can_default: bool = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: NoArgAnyCallable | None | UnsetType = Unset,
        annotation: Any | None | UnsetType = Unset,
        alias: str | None | UnsetType = Unset,
        alias_priority: int | None | UnsetType = Unset,
        validation_alias: str | None | UnsetType = Unset,
        serialization_alias: str | None | UnsetType = Unset,
        title: str | None | UnsetType = Unset,
        description: str | None | UnsetType = Unset,
        gt: float | None | UnsetType = Unset,
        ge: float | None | UnsetType = Unset,
        lt: float | None | UnsetType = Unset,
        le: float | None | UnsetType = Unset,
        min_length: int | None | UnsetType = Unset,
        max_length: int | None | UnsetType = Unset,
        pattern: str | None | UnsetType = Unset,
        discriminator: str | None | UnsetType = Unset,
        strict: bool | None | UnsetType = Unset,
        multiple_of: float | None | UnsetType = Unset,
        allow_inf_nan: bool | None | UnsetType = Unset,
        max_digits: int | None | UnsetType = Unset,
        decimal_places: int | None | UnsetType = Unset,
        deprecated: Deprecated | str | bool | None | UnsetType = Unset,
        examples: List[Any] | None | UnsetType = Unset,
        json_schema_extra: Dict[str, Any] | None | UnsetType = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
        """Initializes a RapidyFieldInfo instance with additional validation and metadata options.

        Args:
            default (Any): Default value for the field. Defaults to Undefined.
            annotation (Union[Any, None, UnsetType]): The type annotation for the field.
            alias (Union[str, None, UnsetType]): Alternative name for serialization and deserialization.
            alias_priority (Union[int, None, UnsetType]): The priority of alias resolution.
            validation_alias (Union[str, None, UnsetType]): Alias used during validation.
            serialization_alias (Union[str, None, UnsetType]): Alias used during serialization.
            default_factory (Union[NoArgAnyCallable, None, UnsetType]): A callable that returns the default value.
            title (Union[str, None, UnsetType]): A human-readable title for the field.
            description (Union[str, None, UnsetType]): A description of the field.
            gt, ge, lt, le (Union[float, None, UnsetType]): Constraints for numerical fields.
            min_length, max_length (Union[int, None, UnsetType]): Constraints for string length.
            pattern (Union[str, None, UnsetType]): A regex pattern for string validation.
            discriminator (Union[str, None, UnsetType]): Discriminator field for polymorphic models.
            strict (Union[bool, None, UnsetType]): Whether to enforce strict type validation.
            multiple_of (Union[float, None, UnsetType]): A constraint for numeric fields.
            allow_inf_nan (Union[bool, None, UnsetType]): Whether NaN and infinity values are allowed.
            max_digits, decimal_places (Union[int, None, UnsetType]): Constraints for decimal precision.
            deprecated (Union[Deprecated, str, bool, None, UnsetType]): Marks the field as deprecated.
            examples (Union[List[Any], None, UnsetType]): Example values for the field.
            json_schema_extra (Union[Dict[str, Any], None, UnsetType]): Extra metadata for JSON Schema.
            validate (bool): Whether to enable field validation. Defaults to True.
            **extra (Any): Additional parameters.
        """
        json_schema_extra = json_schema_extra if json_schema_extra is not Unset else {}

        self.need_validate = validate

        regex = extra.pop('regex', None)

        kwargs = {
            'default': default,
            'default_factory': default_factory,
            'alias': alias,
            'title': title,
            'description': description,
            'gt': gt,
            'ge': ge,
            'lt': lt,
            'le': le,
            'min_length': min_length,
            'max_length': max_length,
            'discriminator': discriminator,
            'multiple_of': multiple_of,
            'allow_inf_nan': allow_inf_nan,
            'max_digits': max_digits,
            'decimal_places': decimal_places,
            **extra,
        }

        if examples is not None:
            kwargs['examples'] = examples

        current_json_schema_extra = json_schema_extra or extra

        if PYDANTIC_IS_V1:
            kwargs['regex'] = self._get_pattern(pattern=pattern, regex=regex)
            kwargs.update(**current_json_schema_extra)
        else:
            kwargs.update(
                {
                    'annotation': annotation,
                    'alias_priority': alias_priority,
                    'validation_alias': validation_alias,
                    'serialization_alias': serialization_alias,
                    'strict': strict,
                    'json_schema_extra': current_json_schema_extra,
                },
            )
            kwargs['pattern'] = self._get_pattern(pattern=pattern, regex=regex)

        if PYDANTIC_VERSION_TUPLE < ('2', '7'):
            self.deprecated = deprecated if deprecated is not Unset else None
        else:
            kwargs['deprecated'] = deprecated

        super().__init__(
            **{key: value for key, value in kwargs.items() if value is not Unset},
        )

        if PYDANTIC_IS_V1:
            self._validate()  # check specify both default and default_factory

    def _get_pattern(self, pattern: str | None | UnsetType, regex: str | None) -> Any:
        """Retrieves the appropriate pattern for validation, handling deprecations.

        Args:
            pattern (Union[str, None, UnsetType]): The pattern value.
            regex (Optional[str]): The regex pattern (deprecated).

        Returns:
            Any: The final pattern value.
        """
        if is_not_none_and_unset(pattern):
            return pattern

        if is_not_none_and_unset(regex):
            warnings.warn(
                '`regex` has been deprecated, please use `pattern` instead',
                category=DeprecationWarning,
                stacklevel=4,
            )
            return regex

        return Unset


if PYDANTIC_IS_V1:

    def copy_field_info(*, field_info: RapidyFieldInfo, annotation: Any) -> RapidyFieldInfo:  # noqa: ARG001
        return deepcopy(field_info)

else:

    def copy_field_info(*, field_info: RapidyFieldInfo, annotation: Any) -> RapidyFieldInfo:
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
