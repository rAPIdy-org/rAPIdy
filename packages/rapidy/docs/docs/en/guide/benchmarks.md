# Benchmarks

The checked-in benchmark is a reproducibility tool, not a marketing claim. Four isolated environments execute the
same Pydantic request/response workload:

- rAPIdy 2.0 + Granian;
- rAPIdy 2.0 + Uvicorn;
- FastAPI + Uvicorn;
- rAPIdy 1.1.2 + aiohttp.

Bombardier 2.0.2 ran on an Apple M4 Pro with 14 cores, concurrency 128, a 5-second warmup, and the median of three
30-second repeats. Every cell had zero non-2xx responses and CV below 5%.

| workers | stand | RPS | p99, ms |
|---:|---|---:|---:|
| 1 | rAPIdy 2.0 + Granian | 11,540 | 25.17 |
| 1 | rAPIdy 2.0 + Uvicorn | 13,805 | 24.74 |
| 1 | FastAPI + Uvicorn | 17,773 | 13.32 |
| 1 | rAPIdy 1.1.2 + aiohttp | 10,299 | 29.96 |
| 14 | rAPIdy 2.0 + Granian | 36,146 | 17.73 |
| 14 | rAPIdy 2.0 + Uvicorn | 45,022 | 4.76 |
| 14 | FastAPI + Uvicorn | 47,033 | 3.72 |
| 14 | rAPIdy 1.1.2 + aiohttp | 46,784 | 6.02 |

At one worker Granian is 1.12× the legacy RPS, but 0.65× FastAPI and 0.84× rAPIdy on Uvicorn. At 14 workers Granian
is 0.77× FastAPI/legacy and 0.80× rAPIdy on Uvicorn. These losses are intentionally preserved in the report.

See the [full generated report](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/benchmarks/RESULTS.md),
[raw JSON](https://github.com/rAPIdy-org/rAPIdy/tree/main/packages/rapidy/benchmarks/results/raw), and
[reproduction commands](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/benchmarks/README.md).
