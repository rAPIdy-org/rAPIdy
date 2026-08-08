from __future__ import annotations

import json
from pathlib import Path

import pytest
from benchmarks._harness import (
    BASELINE_PATH,
    MEMORY_PEAK_LIMIT_BYTES,
    STREAM_CHUNK_BYTES,
    STREAM_TOTAL_BYTES,
    check_baseline,
    measure_stream_memory,
)


def _baseline(tmp_path: Path, *, ratio: float = 0.2) -> Path:
    target = tmp_path / "baseline.json"
    target.write_text(
        json.dumps(
            {
                "gate_variant": "+di",
                "variants": {
                    "no-di": {"relative_overhead_ratio": 0.1},
                    "+di": {"relative_overhead_ratio": ratio},
                },
            }
        ),
        encoding="utf-8",
    )
    return target


def test_check_baseline_passes_when_di_within_threshold(tmp_path: Path) -> None:
    passed, detail = check_baseline(
        {"no-di": 99.0, "+di": 0.22},
        baseline_path=_baseline(tmp_path),
    )
    assert passed
    assert detail["no_di_ratio"] == 99.0
    assert detail["limit"] == pytest.approx(0.23)


def test_check_baseline_fails_when_di_over_threshold(tmp_path: Path) -> None:
    passed, detail = check_baseline(
        {"no-di": 0.0, "+di": 0.24},
        baseline_path=_baseline(tmp_path),
    )
    assert not passed
    assert detail["gate_variant"] == "+di"


@pytest.mark.parametrize("current", [{"+di": 0.2}, {"no-di": 0.1}])
def test_check_baseline_requires_both_variants(
    tmp_path: Path,
    current: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="exactly"):
        check_baseline(current, baseline_path=_baseline(tmp_path))


def test_baseline_json_committed_and_valid() -> None:
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert data["gate_variant"] == "+di"
    for name in ("no-di", "+di"):
        values = data["variants"][name]
        assert isinstance(values["relative_overhead_ratio"], float)
        assert values["environment"]


@pytest.mark.asyncio
async def test_measure_stream_memory_small_within_limit() -> None:
    peak = await measure_stream_memory(total_bytes=4 * 1024 * 1024)
    assert peak < MEMORY_PEAK_LIMIT_BYTES


def test_stream_memory_limit_constants() -> None:
    assert MEMORY_PEAK_LIMIT_BYTES == 32 * 1024 * 1024
    assert STREAM_CHUNK_BYTES == 65536
    assert STREAM_TOTAL_BYTES == 2 * 1024 * 1024 * 1024
