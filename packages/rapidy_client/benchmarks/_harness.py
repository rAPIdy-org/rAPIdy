from __future__ import annotations

import json
import logging
import math
import platform
import statistics
import time
import tracemalloc
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx2
from rapidy_client import (
    Headers,
    HttpClient,
    RedirectConfig,
    Request,
    Response,
    ResponseExtensions,
    UpstreamConfig,
    bind,
)
from rapidy_client.config import LogConfig, rapidy_client_request_id
from rapidy_client.di import HttpApp, provide_endpoint
from rapidy_client.schema import get
from rapidy_client.testing import MockTransport
from rapidy_client.testing.chaos import ChaosServer
from rapidy_core.di import Component

HEADROOM_PATH = Path(__file__).parent / "headroom.json"
BASELINE_PATH = Path(__file__).parent / "baseline.json"
VARIANTS = ("bare_httpx2", "+logging", "+correlation", "+redirect")
LAYER_VARIANTS = (*VARIANTS, "+deadline", "+retry", "full")
FULL_STACK_VARIANTS = ("no-di", "+di")
DI_INCREMENTAL_METRIC = "di-incremental"
FULL_STACK_METRICS = (*FULL_STACK_VARIANTS, DI_INCREMENTAL_METRIC)
BASELINE_VARIANTS = ("bare_httpx2", *FULL_STACK_VARIANTS)
FULL_STACK = "redirect,retry,deadline,logging,correlation"

ADVISORY_P99_US = 300.0
HEADROOM_THRESHOLD_PCT = 10.0
DEFAULT_ITERATIONS = 2000
DEFAULT_WARMUP = 200
DEFAULT_GATE_RUNS = 5
REGRESSION_THRESHOLD_RATIO = 0.15
DI_INCREMENTAL_NOISE_FLOOR_RATIO = 0.10
MEMORY_PEAK_LIMIT_BYTES = 32 * 1024 * 1024
STREAM_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
STREAM_CHUNK_BYTES = 65536


@dataclass(slots=True, kw_only=True)
class VariantResult:
    name: str
    p50_us: float
    p99_us: float
    overhead_pct: float | None


BENCHMARK_COMPONENT = Component("benchmark")


class BenchmarkEndpoint:
    pass


@get("/", deadline=60.0)
async def _benchmark_endpoint() -> Response:
    raise NotImplementedError


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
    config = UpstreamConfig.model_validate(
        {
            "base_url": base_url,
            "log": LogConfig(level="meta"),
            "redirects": RedirectConfig(follow=follow_redirects),
        }
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


def _full_stack_config(base_url: str) -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": base_url,
            "log": LogConfig(level="meta"),
            "redirects": RedirectConfig(follow=True),
        }
    )


async def _measure_bound_endpoint(
    base_url: str,
    *,
    use_di: bool,
    iterations: int,
    warmup: int,
) -> tuple[float, float]:
    token = rapidy_client_request_id.set("benchmark-request")
    try:
        if use_di:
            app = HttpApp(
                upstreams={BENCHMARK_COMPONENT: _full_stack_config(base_url)},
                di_providers=(
                    provide_endpoint(
                        _benchmark_endpoint,
                        provides=BenchmarkEndpoint,
                        component=BENCHMARK_COMPONENT,
                    ),
                ),
            )
            async with app:

                async def call() -> None:
                    endpoint = cast(
                        "Callable[[], Awaitable[Response]]",
                        await app.container.get(BenchmarkEndpoint),
                    )
                    response = await endpoint()
                    if response.status != 200:
                        raise RuntimeError(
                            f"unexpected benchmark status {response.status}"
                        )

                return await _measure(call, iterations=iterations, warmup=warmup)

        client = HttpClient(_full_stack_config(base_url))
        try:
            endpoint = bind(_benchmark_endpoint, client)

            async def call() -> None:
                response = await endpoint()
                if response.status != 200:
                    raise RuntimeError(f"unexpected benchmark status {response.status}")

            return await _measure(call, iterations=iterations, warmup=warmup)
        finally:
            await client.aclose()
    finally:
        rapidy_client_request_id.reset(token)


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
    allowed_variants = {*LAYER_VARIANTS, *FULL_STACK_VARIANTS}
    if any(name not in allowed_variants for name in variants):
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
                elif name in FULL_STACK_VARIANTS:
                    measurement = await _measure_bound_endpoint(
                        server.url,
                        use_di=name == "+di",
                        iterations=iterations,
                        warmup=warmup,
                    )
                else:
                    layer = LAYER_VARIANTS.index(name)
                    measurement = await _measure_client(
                        server.url,
                        request_id=(
                            "benchmark-request"
                            if layer >= LAYER_VARIANTS.index("+correlation")
                            else None
                        ),
                        follow_redirects=layer >= LAYER_VARIANTS.index("+redirect"),
                        enable_deadline=layer >= LAYER_VARIANTS.index("+deadline"),
                        enable_retry=layer >= LAYER_VARIANTS.index("+retry"),
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
    if tuple(by_name) != BASELINE_VARIANTS:
        raise ValueError(f"results must follow variants {BASELINE_VARIANTS!r}")
    requested = {part.strip() for part in stack.split(",") if part.strip()}
    expected = set(FULL_STACK.split(","))
    if requested != expected:
        raise ValueError(f"full-stack baseline requires layers {sorted(expected)!r}")
    bare = by_name["bare_httpx2"]
    environment = {
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    variants: dict[str, object] = {}
    for name in FULL_STACK_VARIANTS:
        result = by_name[name]
        ratio = (result.p50_us - bare.p50_us) / bare.p50_us
        variants[name] = {
            "relative_overhead_ratio": round(ratio, 6),
            "p50_us_advisory": result.p50_us,
            "p99_us_advisory": result.p99_us,
            "environment": dict(environment),
        }
    incremental_ratio = (by_name["+di"].p50_us - by_name["no-di"].p50_us) / bare.p50_us
    return {
        "kind": "baseline",
        "stack": FULL_STACK,
        "auth_included": False,
        "di_included": True,
        "gate_variant": "+di",
        "gate_metric": "di_incremental_overhead_ratio",
        "di_incremental_overhead_ratio": round(incremental_ratio, 6),
        "di_incremental_noise_floor_ratio": DI_INCREMENTAL_NOISE_FLOOR_RATIO,
        "reference": {
            "variant": "bare_httpx2",
            "p50_us_advisory": bare.p50_us,
            "p99_us_advisory": bare.p99_us,
            "environment": environment,
        },
        "variants": variants,
        "samples": samples,
        "frozen_at": datetime.now(UTC).isoformat(),
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


async def measure_full_stack_samples(
    *,
    runs: int = DEFAULT_GATE_RUNS,
    iterations: int = DEFAULT_ITERATIONS,
    warmup: int = DEFAULT_WARMUP,
) -> list[dict[str, float]]:
    if runs <= 0:
        raise ValueError("runs must be greater than zero")
    samples: list[dict[str, float]] = []
    for _ in range(runs):
        results = await run_breakdown(
            iterations=iterations,
            warmup=warmup,
            variants=BASELINE_VARIANTS,
        )
        sample: dict[str, float] = {}
        for result in results[1:]:
            if result.overhead_pct is None:
                raise RuntimeError(f"benchmark variant {result.name!r} has no overhead")
            sample[result.name] = result.overhead_pct / 100.0
        samples.append(sample)
    return samples


def aggregate_full_stack_samples(
    samples: Sequence[Mapping[str, float]],
) -> dict[str, float]:
    if not samples:
        raise ValueError("at least one full-stack sample is required")
    expected = set(FULL_STACK_VARIANTS)
    if any(set(sample) != expected for sample in samples):
        raise ValueError(
            f"each full-stack sample must contain exactly {FULL_STACK_VARIANTS!r}"
        )
    aggregated = {
        variant: float(statistics.median(sample[variant] for sample in samples))
        for variant in FULL_STACK_VARIANTS
    }
    aggregated[DI_INCREMENTAL_METRIC] = float(
        statistics.median(sample["+di"] - sample["no-di"] for sample in samples)
    )
    return aggregated


def check_baseline(
    current: Mapping[str, float],
    *,
    baseline_path: Path = BASELINE_PATH,
    threshold: float = REGRESSION_THRESHOLD_RATIO,
) -> tuple[bool, dict[str, object]]:
    if set(current) != set(FULL_STACK_METRICS):
        raise ValueError(f"current ratios must contain exactly {FULL_STACK_METRICS!r}")
    if threshold < 0:
        raise ValueError("regression threshold must be non-negative")
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    variants = data.get("variants")
    if (
        not isinstance(variants, dict)
        or data.get("gate_variant") != "+di"
        or data.get("gate_metric") != "di_incremental_overhead_ratio"
    ):
        raise ValueError("baseline does not define the incremental +di gate")
    baseline_di = variants.get("+di")
    baseline_no_di = variants.get("no-di")
    if not isinstance(baseline_di, dict) or not isinstance(baseline_no_di, dict):
        raise TypeError("baseline must contain no-di and +di variants")
    try:
        baseline_ratio = float(baseline_di["relative_overhead_ratio"])
        baseline_no_di_ratio = float(baseline_no_di["relative_overhead_ratio"])
        baseline_incremental_ratio = float(data["di_incremental_overhead_ratio"])
        noise_floor_ratio = float(data["di_incremental_noise_floor_ratio"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("baseline variant ratios are invalid") from exc
    if noise_floor_ratio < 0:
        raise ValueError("baseline noise floor must be non-negative")
    limit = max(baseline_incremental_ratio * (1.0 + threshold), noise_floor_ratio)
    current_di = float(current["+di"])
    current_no_di = float(current["no-di"])
    current_incremental_ratio = float(current[DI_INCREMENTAL_METRIC])
    return current_incremental_ratio <= limit, {
        "gate_variant": "+di",
        "baseline_ratio": baseline_ratio,
        "baseline_no_di_ratio": baseline_no_di_ratio,
        "baseline_incremental_ratio": baseline_incremental_ratio,
        "current_incremental_ratio": current_incremental_ratio,
        "di_ratio": current_di,
        "no_di_ratio": current_no_di,
        "limit": limit,
        "noise_floor_ratio": noise_floor_ratio,
        "threshold": threshold,
    }


async def measure_stream_memory(
    *,
    total_bytes: int = STREAM_TOTAL_BYTES,
    chunk_bytes: int = STREAM_CHUNK_BYTES,
) -> int:
    if total_bytes < 0:
        raise ValueError("total_bytes must be non-negative")
    if chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be greater than zero")

    async def chunks() -> AsyncIterator[bytes]:
        remaining = total_bytes
        block = b"x" * chunk_bytes
        while remaining:
            size = min(remaining, chunk_bytes)
            yield block if size == chunk_bytes else block[:size]
            remaining -= size

    async def handler(request: Request) -> Response:
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=1),
            stream=chunks(),
        )

    mock = MockTransport()
    mock.route("GET", "/big").respond_with(handler)
    client = HttpClient(
        UpstreamConfig.model_validate({"base_url": "https://mock.test"}),
        transport=mock,
    )
    tracemalloc.start()
    try:
        async with client.stream("GET", "/big") as response:
            async for _ in response.aiter_bytes(chunk_bytes):
                pass
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
        await client.aclose()


__all__ = (
    "ADVISORY_P99_US",
    "BASELINE_PATH",
    "BASELINE_VARIANTS",
    "DEFAULT_GATE_RUNS",
    "DEFAULT_ITERATIONS",
    "DEFAULT_WARMUP",
    "DI_INCREMENTAL_METRIC",
    "DI_INCREMENTAL_NOISE_FLOOR_RATIO",
    "FULL_STACK",
    "FULL_STACK_METRICS",
    "FULL_STACK_VARIANTS",
    "HEADROOM_PATH",
    "HEADROOM_THRESHOLD_PCT",
    "LAYER_VARIANTS",
    "MEMORY_PEAK_LIMIT_BYTES",
    "REGRESSION_THRESHOLD_RATIO",
    "STREAM_CHUNK_BYTES",
    "STREAM_TOTAL_BYTES",
    "VARIANTS",
    "VariantResult",
    "aggregate_full_stack_samples",
    "build_baseline",
    "build_headroom",
    "check_baseline",
    "format_breakdown",
    "measure_full_stack_samples",
    "measure_stream_memory",
    "run_breakdown",
)
