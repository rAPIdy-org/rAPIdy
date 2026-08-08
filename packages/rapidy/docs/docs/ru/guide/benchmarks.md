# Бенчмарки

Бенчмарк в репозитории — инструмент воспроизводимости, а не маркетинговое утверждение. Четыре изолированных стенда
выполняют одинаковую Pydantic-валидацию входа и выхода. Bombardier 2.0.2 запускался на Apple M4 Pro (14 ядер),
concurrency 128, warmup 5 секунд, медиана трёх повторов по 30 секунд. Во всех ячейках non-2xx = 0 и CV < 5%.

| workers | стенд | RPS | p99, ms |
|---:|---|---:|---:|
| 1 | rAPIdy 2.0 + Granian | 11 540 | 25.17 |
| 1 | rAPIdy 2.0 + Uvicorn | 13 805 | 24.74 |
| 1 | FastAPI + Uvicorn | 17 773 | 13.32 |
| 1 | rAPIdy 1.1.2 + aiohttp | 10 299 | 29.96 |
| 14 | rAPIdy 2.0 + Granian | 36 146 | 17.73 |
| 14 | rAPIdy 2.0 + Uvicorn | 45 022 | 4.76 |
| 14 | FastAPI + Uvicorn | 47 033 | 3.72 |
| 14 | rAPIdy 1.1.2 + aiohttp | 46 784 | 6.02 |

На одном worker Granian быстрее legacy по RPS в 1.12×, но даёт 0.65× RPS FastAPI и 0.84× rAPIdy+Uvicorn. На 14
workers Granian даёт 0.77× RPS FastAPI/legacy и 0.80× rAPIdy+Uvicorn. Проигрыши явно сохранены в отчёте.

[Полный отчёт](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/benchmarks/RESULTS.md) ·
[raw JSON](https://github.com/rAPIdy-org/rAPIdy/tree/main/packages/rapidy/benchmarks/results/raw) ·
[воспроизведение](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/benchmarks/README.md)
