from __future__ import annotations

import asyncio
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aiohttp.test_utils import make_mocked_request
from aiohttp.web_urldispatcher import UrlDispatcher

from spikes.spike_c_matcher.matcher_proto import UrlMatcher

CALLS = 20_000
REPEATS = 7


async def _aiohttp_handler(_request: Any) -> None:
    return None


def _build_rapidy(route_count: int) -> tuple[UrlMatcher, list[str]]:
    matcher = UrlMatcher()
    paths = [f"/items/{index}" for index in range(route_count)]
    for path in paths:
        matcher.add_route("GET", path, _aiohttp_handler)
    return matcher, paths


def _build_aiohttp(route_count: int) -> tuple[UrlDispatcher, list[Any]]:
    dispatcher = UrlDispatcher()
    paths = [f"/items/{index}" for index in range(route_count)]
    for path in paths:
        dispatcher.add_get(path, _aiohttp_handler)
    dispatcher.freeze()
    requests = [make_mocked_request("GET", path) for path in paths]
    return dispatcher, requests


def _median_ns(operation: Callable[[], None], calls: int = CALLS) -> float:
    samples: list[float] = []
    for _ in range(REPEATS):
        started = time.perf_counter_ns()
        operation()
        samples.append((time.perf_counter_ns() - started) / calls)
    return statistics.median(samples)


def _measure_rapidy(route_count: int) -> float:
    matcher, paths = _build_rapidy(route_count)

    def operation() -> None:
        for index in range(CALLS):
            matcher.resolve("GET", paths[index % route_count])

    return _median_ns(operation)


def _measure_aiohttp(route_count: int) -> float:
    dispatcher, requests = _build_aiohttp(route_count)

    async def batch() -> None:
        for index in range(CALLS):
            await dispatcher.resolve(requests[index % route_count])

    def operation() -> None:
        asyncio.run(batch())

    return _median_ns(operation)


def main() -> None:
    rows: list[tuple[int, float, float, float]] = []
    for route_count in (10, 100):
        rapidy_ns = _measure_rapidy(route_count)
        aiohttp_ns = _measure_aiohttp(route_count)
        rows.append((route_count, rapidy_ns, aiohttp_ns, rapidy_ns / aiohttp_ns))

    print("routes rapidy_ns aiohttp_ns ratio")
    for route_count, rapidy_ns, aiohttp_ns, ratio in rows:
        print(f"{route_count:>6} {rapidy_ns:>9.1f} {aiohttp_ns:>10.1f} {ratio:>5.3f}")
    growth = rows[1][1] / rows[0][1]
    print(f"growth_100_over_10 {growth:.3f}")

    if any(row[3] > 1.5 for row in rows):
        raise SystemExit("matcher performance gate failed: ratio > 1.5")
    if growth > 15:
        raise SystemExit("matcher scalability gate failed: growth > 15")


if __name__ == "__main__":
    main()
