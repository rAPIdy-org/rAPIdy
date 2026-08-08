from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, Field
from rapidy_client.schema import ListStyle
from rapidy_client.schema._serialize import serialize_body, serialize_query

query_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)
query_value = st.one_of(query_scalar, st.lists(query_scalar, max_size=8))


@given(st.dictionaries(st.text(min_size=1, max_size=12), query_value, max_size=12))
def test_serialize_query_is_deterministic(values: dict[str, object]) -> None:
    assert serialize_query(values) == serialize_query(values)  # type: ignore[arg-type]


@given(st.lists(query_scalar, max_size=12))
def test_query_styles_are_individually_deterministic(values: list[object]) -> None:
    query = {"value": values}
    assert serialize_query(query) == serialize_query(query)  # type: ignore[arg-type]
    assert serialize_query(query, list_style=ListStyle.CSV) == serialize_query(
        query, list_style=ListStyle.CSV
    )  # type: ignore[arg-type]


class Payload(BaseModel):
    identifier: int = Field(alias="id")
    note: str | None = None
    enabled: bool = True


@given(
    identifier=st.integers(),
    note=st.one_of(st.none(), st.text()),
    enabled=st.booleans(),
    by_alias=st.booleans(),
    exclude_none=st.booleans(),
    exclude_defaults=st.booleans(),
)
def test_serialize_body_and_flags_are_deterministic(
    identifier: int,
    note: str | None,
    enabled: bool,
    by_alias: bool,
    exclude_none: bool,
    exclude_defaults: bool,
) -> None:
    payload = Payload(id=identifier, note=note, enabled=enabled)
    kwargs = {
        "content_type": "application/json",
        "request_by_alias": by_alias,
        "request_exclude_none": exclude_none,
        "request_exclude_defaults": exclude_defaults,
    }

    assert serialize_body(payload, **kwargs) == serialize_body(payload, **kwargs)  # type: ignore[arg-type]
