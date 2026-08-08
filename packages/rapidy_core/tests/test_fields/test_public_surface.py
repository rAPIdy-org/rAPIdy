from rapidy_core import fields
from rapidy_core.fields import RapidyFieldInfo, copy_field_info
from rapidy_core.fields.field_info import RapidyFieldInfo as DirectRapidyFieldInfo


def test_fields_package_exports() -> None:
    assert set(fields.__all__) == {
        "RapidyFieldInfo",
        "copy_field_info",
        "ABCRapidyModelField",
        "ModelFieldCreationError",
        "RapidyModelField",
        "create_model_field",
        "create_model_field_by_annotation",
    }
    assert fields.RapidyFieldInfo is DirectRapidyFieldInfo


def test_dod_import_line() -> None:
    assert RapidyFieldInfo is DirectRapidyFieldInfo
    assert callable(copy_field_info)
