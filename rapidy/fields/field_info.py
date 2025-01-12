import warnings
from copy import deepcopy
from typing import Any, Dict, List, Optional, Union

from pydantic.fields import FieldInfo

from rapidy.annotation_checkers import is_annotated, is_not_none_and_unset
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import Deprecated, NoArgAnyCallable, Undefined, Unset, UnsetType
from rapidy.version import PYDANTIC_VERSION_TUPLE


class RapidyFieldInfo(FieldInfo):
    name: str
    annotation: Any
    can_default: bool = True

    def __init__(
        self,
        default: Any = Undefined,
        *,
        annotation: Union[Any, None, UnsetType] = Unset,
        alias: Union[str, None, UnsetType] = Unset,
        alias_priority: Union[int, None, UnsetType] = Unset,
        validation_alias: Union[str, None, UnsetType] = Unset,
        serialization_alias: Union[str, None, UnsetType] = Unset,
        default_factory: Union[NoArgAnyCallable, None, UnsetType] = Unset,
        title: Union[str, None, UnsetType] = Unset,
        description: Union[str, None, UnsetType] = Unset,
        gt: Union[float, None, UnsetType] = Unset,
        ge: Union[float, None, UnsetType] = Unset,
        lt: Union[float, None, UnsetType] = Unset,
        le: Union[float, None, UnsetType] = Unset,
        min_length: Union[int, None, UnsetType] = Unset,
        max_length: Union[int, None, UnsetType] = Unset,
        pattern: Union[str, None, UnsetType] = Unset,
        discriminator: Union[str, None, UnsetType] = Unset,
        strict: Union[bool, None, UnsetType] = Unset,
        multiple_of: Union[float, None, UnsetType] = Unset,
        allow_inf_nan: Union[bool, None, UnsetType] = Unset,
        max_digits: Union[int, None, UnsetType] = Unset,
        decimal_places: Union[int, None, UnsetType] = Unset,
        deprecated: Union[Deprecated, str, bool, None, UnsetType] = Unset,
        examples: Union[List[Any], None, UnsetType] = Unset,
        json_schema_extra: Union[Dict[str, Any], None, UnsetType] = Unset,
        validate: bool = True,
        **extra: Any,
    ) -> None:
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
            self.deprecated = deprecated
        else:
            kwargs['deprecated'] = deprecated

        super().__init__(
            **{key: value for key, value in kwargs.items() if value is not Unset},
        )

        if PYDANTIC_IS_V1:
            self._validate()  # check specify both default and default_factory

    def _get_pattern(self, pattern: Union[str, None, UnsetType], regex: Optional[str]) -> Any:
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
        # FIXME:  # noqa: FIX001, TD002
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
