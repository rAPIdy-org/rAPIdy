from abc import ABC
from importlib import import_module
from inspect import signature

import pytest
from rapidy_core.constants import DEFAULT_JSON_DECODER
from rapidy_core.enums import ContentType, HTTPRequestParamType
from rapidy_core.fields.field_info import RapidyFieldInfo
from rapidy_core.parameters import http
from rapidy_core.parameters.http import (
    Body,
    Cookie,
    CookieBase,
    Cookies,
    Header,
    HeaderBase,
    Headers,
    PathBase,
    PathParam,
    PathParams,
    QueryBase,
    QueryParam,
    QueryParams,
    RequestParamFieldInfo,
)
from rapidy_core.typedefs import Undefined

PUBLIC_MARKERS = (
    PathParam,
    PathParams,
    Header,
    Headers,
    Cookie,
    Cookies,
    QueryParam,
    QueryParams,
    Body,
)


def test_all_exports_are_exactly_nine_public_names() -> None:
    assert set(http.__all__) == {
        "Body",
        "Cookie",
        "Cookies",
        "Header",
        "Headers",
        "PathParam",
        "PathParams",
        "QueryParam",
        "QueryParams",
    }
    assert len(http.__all__) == 9


@pytest.mark.parametrize(
    "name",
    (
        *http.__all__,
        "RequestParamFieldInfo",
        "PathBase",
        "HeaderBase",
        "CookieBase",
        "QueryBase",
    ),
)
def test_all_public_names_importable(name: str) -> None:
    module = import_module("rapidy_core.parameters.http")
    assert getattr(module, name) is not None


@pytest.mark.parametrize("marker", PUBLIC_MARKERS)
def test_each_marker_and_aggregate_instantiates(marker: type[RapidyFieldInfo]) -> None:
    assert isinstance(marker(), RapidyFieldInfo)


def test_hierarchy_ascends_to_rapidy_field_info() -> None:
    assert issubclass(RequestParamFieldInfo, RapidyFieldInfo)
    assert issubclass(PathBase, RequestParamFieldInfo)
    assert issubclass(PathParam, PathBase)
    assert issubclass(PathParams, PathBase)
    assert issubclass(Header, HeaderBase)
    assert issubclass(Headers, HeaderBase)
    assert issubclass(Cookie, CookieBase)
    assert issubclass(Cookies, CookieBase)
    assert issubclass(QueryParam, QueryBase)
    assert issubclass(QueryParams, QueryBase)
    assert issubclass(Body, RequestParamFieldInfo)


def test_param_type_per_family() -> None:
    assert PathParam.param_type is PathParams.param_type is HTTPRequestParamType.path
    assert Header.param_type is Headers.param_type is HTTPRequestParamType.header
    assert Cookie.param_type is Cookies.param_type is HTTPRequestParamType.cookie
    assert QueryParam.param_type is QueryParams.param_type is HTTPRequestParamType.query
    assert Body.param_type is HTTPRequestParamType.body


def test_extract_single_flags() -> None:
    for marker in (PathParam, Header, Cookie, QueryParam):
        assert marker.extract_single is True
    for marker in (PathParams, Headers, Cookies, QueryParams, Body):
        assert marker.extract_single is False


def test_path_markers_cannot_default_others_can() -> None:
    assert PathParam.can_default is False
    assert PathParams.can_default is False
    for marker in (Header, Headers, Cookie, Cookies, QueryParam, QueryParams, Body):
        assert marker.can_default is True


def test_pydantic_field_set_on_single_marker() -> None:
    marker = PathParam(
        default="d",
        alias="x",
        serialization_alias="y",
        ge=1,
        le=10,
        min_length=2,
    )

    assert marker.default == "d"
    assert marker.alias == "x"
    assert marker.serialization_alias == "y"
    assert any(getattr(item, "ge", None) == 1 for item in marker.metadata)
    assert any(getattr(item, "le", None) == 10 for item in marker.metadata)
    assert any(getattr(item, "min_length", None) == 2 for item in marker.metadata)


def test_default_factory_passthrough() -> None:
    marker = QueryParam(default_factory=lambda: 42)

    assert marker.default_factory is not None
    assert marker.default_factory() == 42
    assert marker.default is Undefined


def test_body_content_type_defaults() -> None:
    marker = Body()

    assert marker.content_type is ContentType.json
    assert marker.check_content_type is True
    assert marker.json_decoder is DEFAULT_JSON_DECODER
    assert marker.param_type is HTTPRequestParamType.body


def test_body_content_type_and_decoder_override() -> None:
    def decoder(value: str) -> dict[str, str]:
        return {"value": value}

    marker = Body(
        content_type="text/csv",
        check_content_type=False,
        json_decoder=decoder,
    )

    assert marker.content_type == "text/csv"
    assert marker.check_content_type is False
    assert marker.json_decoder is decoder
    assert (
        Body(content_type=ContentType.x_www_form).content_type is ContentType.x_www_form
    )


@pytest.mark.parametrize("marker", PUBLIC_MARKERS)
def test_markers_have_no_client_specific_fields(marker: type[RapidyFieldInfo]) -> None:
    parameters = signature(marker.__init__).parameters
    assert "style" not in parameters
    assert "query_serialization" not in parameters


def test_alias_group_asymmetry_matches_reference() -> None:
    for marker in (PathParam, PathParams, Header, Headers, Cookie, QueryParam):
        assert "alias" in signature(marker.__init__).parameters
    for marker in (Cookies, QueryParams, Body):
        assert "alias" not in signature(marker.__init__).parameters


def test_single_marker_field_set_is_canonical() -> None:
    actual = set(signature(PathParam.__init__).parameters) - {"self", "extra"}
    assert actual == {
        "alias",
        "alias_priority",
        "allow_inf_nan",
        "decimal_places",
        "default",
        "default_factory",
        "deprecated",
        "description",
        "discriminator",
        "examples",
        "ge",
        "gt",
        "json_schema_extra",
        "le",
        "lt",
        "max_digits",
        "max_length",
        "min_length",
        "multiple_of",
        "pattern",
        "serialization_alias",
        "strict",
        "title",
        "validate",
        "validation_alias",
    }


@pytest.mark.parametrize(
    "base",
    (RequestParamFieldInfo, PathBase, HeaderBase, CookieBase, QueryBase),
)
def test_base_classes_are_abstract_marker_only(
    base: type[RequestParamFieldInfo],
) -> None:
    assert ABC in base.__mro__
