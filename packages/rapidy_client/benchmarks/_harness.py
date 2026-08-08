from __future__ import annotations

import logging
import math
import platform
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx2
from rapidy_client import HttpClient, RedirectConfig, UpstreamConfig
from rapidy_client.config import LogConfig, rapidy_client_request_id
from rapidy_client.testing.chaos import ChaosServer

HEADROOM_PATH = Path(__file__).parent / "headroom.json"
BASELINE_PATH = Path(__file__).parent / "baseline.json"
VARIANTS = ("bare_httpx2", "+logging", "+correlation", "+redirect")
FULL_STACK_VARIANTS = VARIANTS + ("+deadline", "+retry", "full")
FULL_STACK = "redirect,retry,deadline,logging,correlation"

ADVISORY_P99_US = 300.0
HEADROOM_THRESHOLD_PCT = 10.0
DEFAULT_ITERATIONS = 2000
DEFAULT_WARMUP = 200


@dataclass(slots=True, kw_only=True)
class VariantResult:
    name: str
    p50_us: float
    p99_us: float
    overhead_pct: float | None


def _percentile(values: list[int], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index] / 1000


async def _measure(
    call: Callable[[], Awaitable[None]],
    *,
    iterations: int,
    warmup: int,
) -> tuple[float, float]:
    for _ in range(warmup):
        await call()
    durations: list[int] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        await call()
        durations.append(time.perf_counter_ns() - started)
    return _percentile(durations, 0.50), _percentile(durations, 0.99)


async def _measure_bare(
    base_url: str,
    *,
    iterations: int,
    warmup: int,
) -> tuple[float, float]:
    async with httpx2.AsyncClient(
        base_url=base_url,
        follow_redirects=False,
    ) as client:

        async def call() -> None:
            response = await client.get("/")
            if response.status_code != 200:
                raise RuntimeError(
                    f"unexpected benchmark status {response.status_code}"
                )

        return await _measure(call, iterations=iterations, warmup=warmup)


async def _measure_client(
    base_url: str,
    *,
    request_id: str | None,
    follow_redirects: bool,
    enable_deadline: bool,
    enable_retry: bool,
    iterations: int,
    warmup: int,
) -> tuple[float, float]:
    config = UpstreamConfig(
        base_url=base_url,
        log=LogConfig(level="meta"),
        redirects=RedirectConfig(follow=follow_redirects),
    )
    client = HttpClient(config)
    token = rapidy_client_request_id.set(request_id)
    try:

        async def call() -> None:
            if enable_deadline and enable_retry:
                response = await client.get("/", deadline=60.0)
            elif enable_deadline:
                response = await client.get("/", deadline=60.0, retry=None)
            elif enable_retry:
                response = await client.get("/")
            else:
                response = await client.get("/", retry=None)
            if response.status != 200:
                raise RuntimeError(f"unexpected benchmark status {response.status}")

        return await _measure(call, iterations=iterations, warmup=warmup)
    finally:
        rapidy_client_request_id.reset(token)
        await client.aclose()


async def run_breakdown(
    *,
    iterations: int = DEFAULT_ITERATIONS,
    warmup: int = DEFAULT_WARMUP,
    variants: tuple[str, ...] = VARIANTS,
) -> list[VariantResult]:
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")
    if not variants or variants[0] != "bare_httpx2":
        raise ValueError("variants must start with bare_httpx2")
    if any(name not in FULL_STACK_VARIANTS for name in variants):
        raise ValueError(f"unknown benchmark variant in {variants!r}")

    logger = logging.getLogger("rapidy_client.http")
    previous_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)
    try:
        async with ChaosServer().respond_ok(body=b"ok") as server:
            raw: list[tuple[str, tuple[float, float]]] = []
            for name in variants:
                if name == "bare_httpx2":
                    measurement = await _measure_bare(
                        server.url,
                        iterations=iterations,
                        warmup=warmup,
                    )
                else:
                    layer = FULL_STACK_VARIANTS.index(name)
                    measurement = await _measure_client(
                        server.url,
                        request_id=(
                            "benchmark-request"
                            if layer >= FULL_STACK_VARIANTS.index("+correlation")
                            else None
                        ),
                        follow_redirects=layer
                        >= FULL_STACK_VARIANTS.index("+redirect"),
                        enable_deadline=layer >= FULL_STACK_VARIANTS.index("+deadline"),
                        enable_retry=layer >= FULL_STACK_VARIANTS.index("+retry"),
                        iterations=iterations,
                        warmup=warmup,
                    )
                raw.append((name, measurement))
    finally:
        logger.setLevel(previous_level)

    bare_p50 = raw[0][1][0]
    results: list[VariantResult] = []
    for name, (p50, p99) in raw:
        overhead = None if name == "bare_httpx2" else (p50 - bare_p50) / bare_p50 * 100
        results.append(
            VariantResult(
                name=name,
                p50_us=round(p50, 3),
                p99_us=round(p99, 3),
                overhead_pct=None if overhead is None else round(overhead, 3),
            )
        )
    return results


def build_headroom(results: list[VariantResult]) -> dict[str, object]:
    by_name = {result.name: result for result in results}
    if tuple(by_name) != VARIANTS:
        raise ValueError(f"results must follow variants {VARIANTS!r}")
    final = by_name["+redirect"]
    overhead = final.overhead_pct if final.overhead_pct is not None else 0.0
    return {
        "schema": "rapidy-client/headroom@1",
        "kind": "bring-up-headroom",
        "gate": False,
        "phase": "F1",
        "stack": "pipeline+logging+correlation+redirect",
        "reference": "bare_httpx2",
        "metric": "relative_overhead_pct",
        "iterations": DEFAULT_ITERATIONS,
        "warmup": DEFAULT_WARMUP,
        "advisory_p99_us": ADVISORY_P99_US,
        "threshold_pct": HEADROOM_THRESHOLD_PCT,
        "variants": {
            result.name: {
                "p50_us": result.p50_us,
                "p99_us": result.p99_us,
                "overhead_pct": result.overhead_pct,
            }
            for result in results
        },
        "headroom": {
            "overhead_pct": overhead,
            "p99_us": final.p99_us,
            "within_threshold": overhead <= HEADROOM_THRESHOLD_PCT,
            "within_advisory_p99": final.p99_us <= ADVISORY_P99_US,
        },
    }


def build_baseline(
    results: list[VariantResult],
    *,
    stack: str = FULL_STACK,
    samples: int = DEFAULT_ITERATIONS,
) -> dict[str, object]:
    by_name = {result.name: result for result in results}
    if tuple(by_name) != FULL_STACK_VARIANTS:
        raise ValueError(f"results must follow variants {FULL_STACK_VARIANTS!r}")
    requested = {part.strip() for part in stack.split(",") if part.strip()}
    expected = set(FULL_STACK.split(","))
    if requested != expected:
        raise ValueError(f"full-stack baseline requires layers {sorted(expected)!r}")
    bare = by_name["bare_httpx2"]
    full = by_name["full"]
    ratio = (full.p50_us - bare.p50_us) / bare.p50_us
    return {
        "kind": "baseline",
        "stack": FULL_STACK,
        "auth_included": False,
        "di_included": False,
        "relative_overhead_ratio": round(ratio, 6),
        "bare_httpx2_us_advisory": bare.p50_us,
        "full_stack_us_advisory": full.p50_us,
        "samples": samples,
        "machine": platform.node(),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }


def format_breakdown(results: list[VariantResult]) -> str:
    lines = ["variant          p50_us     p99_us   overhead_pct"]
    for result in results:
        overhead = "-" if result.overhead_pct is None else f"{result.overhead_pct:.3f}"
        lines.append(
            f"{result.name:<16} {result.p50_us:>9.3f} "
            f"{result.p99_us:>10.3f} {overhead:>14}"
        )
    return "\n".join(lines)


__all__ = (
    "ADVISORY_P99_US",
    "BASELINE_PATH",
    "DEFAULT_ITERATIONS",
    "DEFAULT_WARMUP",
    "FULL_STACK",
    "FULL_STACK_VARIANTS",
    "HEADROOM_PATH",
    "HEADROOM_THRESHOLD_PCT",
    "VARIANTS",
    "VariantResult",
    "build_baseline",
    "build_headroom",
    "format_breakdown",
    "run_breakdown",
)
