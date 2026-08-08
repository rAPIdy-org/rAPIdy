from __future__ import annotations

import json

import pytest
from benchmarks import (
    HEADROOM_PATH,
    VARIANTS,
    VariantResult,
    build_headroom,
    format_breakdown,
    run_breakdown,
)


def _results() -> list[VariantResult]:
    return [
        VariantResult(
            name=name,
            p50_us=100.0 + index,
            p99_us=150.0 + index,
            overhead_pct=None if index == 0 else float(index),
        )
        for index, name in enumerate(VARIANTS)
    ]


@pytest.mark.asyncio
async def test_run_breakdown_smoke() -> None:
    results = await run_breakdown(iterations=5, warmup=1)
    assert tuple(result.name for result in results) == VARIANTS
    assert results[0].overhead_pct is None
    assert all(isinstance(result.overhead_pct, float) for result in results[1:])


def test_build_headroom_shape() -> None:
    data = build_headroom(_results())
    assert data["schema"] == "rapidy-client/headroom@1"
    assert data["kind"] == "bring-up-headroom"
    assert data["gate"] is False
    assert set(data["variants"]) == set(VARIANTS)  # type: ignore[arg-type]
    headroom = data["headroom"]
    assert isinstance(headroom, dict)
    assert headroom["overhead_pct"] == 3.0


def test_headroom_json_committed_and_valid() -> None:
    data = json.loads(HEADROOM_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "rapidy-client/headroom@1"
    assert data["kind"] == "bring-up-headroom"
    assert data["gate"] is False
    assert tuple(data["variants"]) == VARIANTS


def test_format_breakdown_prints_all_variants() -> None:
    rendered = format_breakdown(_results())
    assert all(name in rendered for name in VARIANTS)
