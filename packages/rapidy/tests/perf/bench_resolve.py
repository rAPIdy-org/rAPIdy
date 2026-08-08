# ruff: noqa: T201
from __future__ import annotations

import statistics
import sys
import time
from collections.abc import Callable
from contextlib import suppress

from rapidy.exceptions import HTTPNotFound
from rapidy.request import Request
from rapidy.response import Response
from rapidy.routing.matcher import UrlMatcher

ITERATIONS = 100_000
REPEATS = 3
ROUTE_COUNTS = (1, 10, 100)
MAX_GROWTH = 15.0


async def terminal(_: Request) -> Response:
    return Response('ok')


def build_matcher(route_count: int) -> UrlMatcher:
    matcher = UrlMatcher()
    for index in range(4):
        matcher.add_route('GET', f'/static/{index}', terminal, {})
    for index in range(route_count):
        matcher.add_route('GET', rf'/dynamic/{index}/{{value:\d+}}', terminal, {})
    return matcher


def median_ns(operation: Callable[[], None]) -> float:
    samples: list[float] = []
    for _ in range(REPEATS):
        started = time.perf_counter_ns()
        for _ in range(ITERATIONS):
            operation()
        samples.append((time.perf_counter_ns() - started) / ITERATIONS)
    return statistics.median(samples)


def measure(route_count: int) -> dict[str, float]:
    matcher = build_matcher(route_count)

    def static_hit() -> None:
        matcher.resolve('GET', '/static/3')

    def dynamic_hit() -> None:
        matcher.resolve('GET', f'/dynamic/{route_count - 1}/42')

    def miss() -> None:
        with suppress(HTTPNotFound):
            matcher.resolve('GET', '/missing')

    return {
        'static': median_ns(static_hit),
        'dynamic': median_ns(dynamic_hit),
        'miss': median_ns(miss),
    }


def main() -> int:
    results = {route_count: measure(route_count) for route_count in ROUTE_COUNTS}
    print('routes static_ns dynamic_ns miss_ns')
    for route_count in ROUTE_COUNTS:
        row = results[route_count]
        print(f'{route_count:>6} {row["static"]:>9.1f} {row["dynamic"]:>10.1f} {row["miss"]:>7.1f}')

    dynamic_growth = results[100]['dynamic'] / results[10]['dynamic']
    miss_growth = results[100]['miss'] / results[10]['miss']
    print(f'dynamic_growth_100_over_10 {dynamic_growth:.3f}')
    print(f'miss_growth_100_over_10 {miss_growth:.3f}')
    return 0 if dynamic_growth <= MAX_GROWTH and miss_growth <= MAX_GROWTH else 1


if __name__ == '__main__':
    sys.exit(main())
