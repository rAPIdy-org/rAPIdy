from __future__ import annotations

import tomllib
from pathlib import Path

import rapidy_core
from rapidy_core import CORE_API_VERSION, __version__

EXPECTED_ROOT_EXPORTS = {
    "CORE_API_VERSION",
    "UNSET",
    "Charset",
    "ClientBaseError",
    "ClientError",
    "ContentType",
    "HTTPMethod",
    "HTTPRequestParamType",
    "HeaderName",
    "RapidyException",
    "RequiredFieldIsMissingError",
    "Unset",
    "__version__",
    "is_annotated",
    "is_empty",
    "is_optional",
    "is_union",
    "lenient_issubclass",
    "normalize_errors",
    "regenerate_error_with_loc",
}


def test_core_version_matches_distribution_metadata() -> None:
    manifest = Path(__file__).parents[1] / "pyproject.toml"
    with manifest.open("rb") as manifest_file:
        project_version = tomllib.load(manifest_file)["project"]["version"]

    assert __version__ == project_version
    assert CORE_API_VERSION == 1


def test_core_root_surface_is_explicit() -> None:
    assert set(rapidy_core.__all__) == EXPECTED_ROOT_EXPORTS
