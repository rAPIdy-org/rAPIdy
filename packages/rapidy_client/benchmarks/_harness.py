from __future__ import annotations

import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import httpx2
from rapidy_client import HttpClient, RedirectConfig, UpstreamConfig
from rapidy_client.config import LogConfig, rapidy_client_request_id
from rapidy_client.testing.chaos import ChaosServer

HEADROOM_PATH = Path(__file__).parent / "headroom.json"
VARIANTS = ("bare_httpx2", "+logging", "+correlation", "+redirect")

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
            response = await client.get("/")
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
) -> list[VariantResult]:
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")

    logger = logging.getLogger("rapidy_client.http")
    previous_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)
    try:
        async with ChaosServer().respond_ok(body=b"ok") as server:
            raw = [
                (
                    "bare_httpx2",
                    await _measure_bare(
                        server.url,
                        iterations=iterations,
                        warmup=warmup,
                    ),
                ),
                (
                    "+logging",
                    await _measure_client(
                        server.url,
                        request_id=None,
                        follow_redirects=False,
                        iterations=iterations,
                        warmup=warmup,
                    ),
                ),
                (
                    "+correlation",
                    await _measure_client(
                        server.url,
                        request_id="benchmark-request",
                        follow_redirects=False,
                        iterations=iterations,
                        warmup=warmup,
                    ),
                ),
                (
                    "+redirect",
                    await _measure_client(
                        server.url,
                        request_id="benchmark-request",
                        follow_redirects=True,
                        iterations=iterations,
                        warmup=warmup,
                    ),
                ),
            ]
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
    "DEFAULT_ITERATIONS",
    "DEFAULT_WARMUP",
    "HEADROOM_PATH",
    "HEADROOM_THRESHOLD_PCT",
    "VARIANTS",
    "VariantResult",
    "build_headroom",
    "format_breakdown",
    "run_breakdown",
)
