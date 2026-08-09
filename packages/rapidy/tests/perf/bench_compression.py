# ruff: noqa: T201
from __future__ import annotations

import argparse
import asyncio
import gzip
import statistics
import time
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

from rapidy import Rapidy
from rapidy.http import get, Response
from rapidy.middlewares import CompressionMiddleware

PAYLOAD = b'{"message":"production middleware benchmark","values":[1,2,3,4,5]}' * 1024
REPEATS = 5


@dataclass(frozen=True, slots=True)
class Measurement:
    algorithm: str
    median_us: float
    encoded_size: int
    ratio: float


def build_app(algorithm: str | None) -> Rapidy:
    @get('/')
    async def payload() -> Response:
        return Response(PAYLOAD, content_type='application/json')

    middlewares = [] if algorithm is None else [CompressionMiddleware(algorithms=[algorithm], minimum_size=1)]
    return Rapidy(middlewares=middlewares, http_route_handlers=[payload])


async def one_request(app: Rapidy, algorithm: str | None) -> bytes:
    body = bytearray()

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message: dict[str, Any]) -> None:
        if message['type'] == 'http.response.body':
            body.extend(message.get('body', b''))

    headers = [(b'host', b'benchmark')]
    if algorithm is not None:
        headers.append((b'accept-encoding', algorithm.encode()))
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'https',
        'path': '/',
        'raw_path': b'/',
        'query_string': b'',
        'headers': headers,
        'client': ('127.0.0.1', 50000),
        'server': ('benchmark', 443),
        'state': {},
    }
    await app(scope, receive, send)
    return bytes(body)


async def measure(algorithm: str | None, iterations: int) -> Measurement:
    app = build_app(algorithm)
    samples: list[float] = []
    encoded = b''
    async with app.lifespan.ctx_manager():
        for _ in range(REPEATS):
            started = time.perf_counter_ns()
            for _ in range(iterations):
                encoded = await one_request(app, algorithm)
            samples.append((time.perf_counter_ns() - started) / iterations / 1000)

    if algorithm == 'gzip':
        assert gzip.decompress(encoded) == PAYLOAD
    elif algorithm == 'br':
        import brotli  # noqa: PLC0415

        assert brotli.decompress(encoded) == PAYLOAD
    else:
        assert encoded == PAYLOAD
    return Measurement(
        algorithm=algorithm or 'identity',
        median_us=statistics.median(samples),
        encoded_size=len(encoded),
        ratio=len(encoded) / len(PAYLOAD),
    )


async def async_main(iterations: int) -> int:
    algorithms: list[str | None] = [None, 'gzip']
    if find_spec('brotli') is not None:
        algorithms.append('br')
    measurements = [await measure(algorithm, iterations) for algorithm in algorithms]
    print(f'payload_bytes={len(PAYLOAD)} iterations={iterations} repeats={REPEATS}')
    print('algorithm median_us encoded_bytes ratio')
    for item in measurements:
        print(f'{item.algorithm:>9} {item.median_us:>9.1f} {item.encoded_size:>13} {item.ratio:>6.3f}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=500)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error('--iterations must be positive')
    return asyncio.run(async_main(args.iterations))


if __name__ == '__main__':
    raise SystemExit(main())
