from __future__ import annotations

import json

import pytest
from benchmarks import (
    BASELINE_PATH,
    BASELINE_VARIANTS,
    FULL_STACK,
    FULL_STACK_VARIANTS,
    HEADROOM_PATH,
    LAYER_VARIANTS,
    VARIANTS,
    VariantResult,
    build_baseline,
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


@pytest.mark.asyncio
async def test_run_full_stack_breakdown_smoke() -> None:
    results = await run_breakdown(
        iterations=2,
        warmup=0,
        variants=BASELINE_VARIANTS,
    )
    assert tuple(result.name for result in results) == BASELINE_VARIANTS


def test_layer_breakdown_still_contains_full_stack() -> None:
    assert LAYER_VARIANTS[-3:] == ("+deadline", "+retry", "full")


def test_build_headroom_shape() -> None:
    data = build_headroom(_results())
    assert data["schema"] == "rapidy-client/headroom@1"
    assert data["kind"] == "bring-up-headroom"
    assert data["gate"] is False
    assert set(data["variants"]) == set(VARIANTS)  # type: ignore[arg-type]
    headroom = data["headroom"]
    assert isinstance(headroom, dict)
    assert headroom["overhead_pct"] == 3.0


def test_build_baseline_shape() -> None:
    results = [
        VariantResult(
            name=name,
            p50_us=100.0 + index,
            p99_us=150.0 + index,
            overhead_pct=None if index == 0 else float(index),
        )
        for index, name in enumerate(BASELINE_VARIANTS)
    ]

    data = build_baseline(results, stack=FULL_STACK, samples=25)

    assert data["kind"] == "baseline"
    assert data["stack"] == FULL_STACK
    assert data["auth_included"] is False
    assert data["di_included"] is True
    assert data["gate_variant"] == "+di"
    assert data["gate_metric"] == "di_incremental_overhead_ratio"
    assert data["di_incremental_overhead_ratio"] == 0.01
    assert data["di_incremental_noise_floor_ratio"] == 0.1
    assert data["samples"] == 25
    variants = data["variants"]
    assert isinstance(variants, dict)
    assert tuple(variants) == FULL_STACK_VARIANTS
    assert variants["no-di"]["relative_overhead_ratio"] == 0.01
    assert variants["+di"]["relative_overhead_ratio"] == 0.02


def test_headroom_json_committed_and_valid() -> None:
    data = json.loads(HEADROOM_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "rapidy-client/headroom@1"
    assert data["kind"] == "bring-up-headroom"
    assert data["gate"] is False
    assert tuple(data["variants"]) == VARIANTS


def test_baseline_json_committed_and_valid() -> None:
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert data["kind"] == "baseline"
    assert data["stack"] == FULL_STACK
    assert data["auth_included"] is False
    assert data["di_included"] is True
    assert data["gate_variant"] == "+di"
    assert data["gate_metric"] == "di_incremental_overhead_ratio"
    assert tuple(data["variants"]) == FULL_STACK_VARIANTS


def test_format_breakdown_prints_all_variants() -> None:
    rendered = format_breakdown(_results())
    assert all(name in rendered for name in VARIANTS)
