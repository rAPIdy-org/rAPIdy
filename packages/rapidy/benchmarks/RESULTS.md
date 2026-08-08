# rAPIdy 2.0 — результаты бенчмарков

Сгенерировано `benchmarks/report.py` из `benchmarks/results/raw/`; вручную не редактировать.

## Окружение

- Дата последнего замера: `2026-08-09T00:19:40`.
- CPU: Apple M4 Pro (14 логических ядер).
- RAM: 24.0 GiB.
- ОС: `macOS-26.6-arm64-arm-64bit-Mach-O`.
- Python: `Python 3.13.3`.
- Инструмент нагрузки: `bombardier` — `bombardier version 2.0.2 darwin/arm64`.

Версии пакетов по стендам:
- `rapidy2-granian`: `granian==2.8.1`, `pydantic==2.13.4`, `rapidy==2.0.0`
- `rapidy2-uvicorn`: `pydantic==2.13.4`, `rapidy==2.0.0`, `uvicorn==0.52.1`
- `fastapi-uvicorn`: `fastapi==0.139.2`, `pydantic==2.13.4`, `uvicorn==0.52.1`
- `rapidy1-aiohttp`: `aiohttp==3.14.2`, `gunicorn==26.0.0`, `pydantic==2.13.4`, `rapidy==1.1.2`

## Методика

Во всех стендах один сценарий: `POST /users` принимает `UserIn`, валидирует JSON и возвращает `UserOut` с `processed=true`. Приложения находятся в `benchmarks/apps/app_rapidy2.py`, `benchmarks/apps/app_fastapi.py` и `benchmarks/apps/app_rapidy1.py`; общие модели — в `benchmarks/common/models.py`, payload — в `benchmarks/common/payload.json`.

Нагрузка: concurrency=128, duration=30 s, warmup=5 s; итог — медиана из 3 повторов. Генератор нагрузки работает на той же машине, поэтому многоворкерные числа консервативны. Каждый стенд использует отдельный `.venv-bench/<stand>`: PyPI-пакеты rAPIdy 1.x и 2.0 одноимённы. Версия pydantic одинакова во всех окружениях.

Вход и выход валидируются штатными средствами: `response_validate=True` у rAPIdy 2.0 и rAPIdy 1.x, `response_model` у FastAPI. Access-log выключен. Uvicorn всегда запускается с `--loop uvloop --http httptools`. Для rAPIdy 1.x при workers > 1 используется gunicorn + `aiohttp.GunicornWebWorker`; из-за другого process manager эта таблица частично сравнивает «яблоки с грушами», тогда как workers=1 — чистое сравнение одного процесса. Абсолютные числа сопоставимы только внутри одной таблицы.

### workers = 1

| Стенд | RPS | p50, ms | p95, ms | p99, ms | CV |
|---|---:|---:|---:|---:|---:|
| rapidy2-granian | 11540 | 10.44 | 14.75 | 25.17 | 3.1% |
| rapidy2-uvicorn | 13805 | 8.82 | 12.70 | 24.74 | 0.6% |
| fastapi-uvicorn | 17773 | 7.83 | 10.64 | 13.32 | 4.8% |
| rapidy1-aiohttp | 10299 | 11.64 | 15.48 | 29.96 | 0.3% |

### workers = 14

| Стенд | RPS | p50, ms | p95, ms | p99, ms | CV |
|---|---:|---:|---:|---:|---:|
| rapidy2-granian | 36146 | 2.87 | 8.35 | 17.73 | 1.7% |
| rapidy2-uvicorn | 45022 | 2.76 | 3.62 | 4.76 | 0.6% |
| fastapi-uvicorn | 47033 | 2.70 | 3.08 | 3.72 | 0.8% |
| rapidy1-aiohttp | 46784 | 2.57 | 3.85 | 6.02 | 0.8% |

## Выводы

- rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=1: RPS ×0.65 (11540 vs 17773), p99 +11.85 ms (25.17 vs 13.32).
- rAPIdy 2.0+Granian vs rAPIdy 1.x (aiohttp), workers=1: RPS ×1.12 (11540 vs 10299), p99 -4.79 ms (25.17 vs 29.96).
- rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=1: RPS ×0.84 (11540 vs 13805), p99 +0.43 ms (25.17 vs 24.74).
- rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=14: RPS ×0.77 (36146 vs 47033), p99 +14.01 ms (17.73 vs 3.72).
- rAPIdy 2.0+Granian vs rAPIdy 1.x (aiohttp), workers=14: RPS ×0.77 (36146 vs 46784), p99 +11.71 ms (17.73 vs 6.02).
- rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=14: RPS ×0.80 (36146 vs 45022), p99 +12.97 ms (17.73 vs 4.76).

### Где проигрываем / паритет

- Проигрыш по RPS — rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=1: ×0.65 (11540 vs 17773).
- Проигрыш по p99 — rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=1: +11.85 ms (25.17 vs 13.32).
- Проигрыш по RPS — rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=1: ×0.84 (11540 vs 13805).
- Проигрыш по p99 — rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=1: +0.43 ms (25.17 vs 24.74).
- Проигрыш по RPS — rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=14: ×0.77 (36146 vs 47033).
- Проигрыш по p99 — rAPIdy 2.0+Granian vs FastAPI+uvicorn, workers=14: +14.01 ms (17.73 vs 3.72).
- Проигрыш по RPS — rAPIdy 2.0+Granian vs rAPIdy 1.x (aiohttp), workers=14: ×0.77 (36146 vs 46784).
- Проигрыш по p99 — rAPIdy 2.0+Granian vs rAPIdy 1.x (aiohttp), workers=14: +11.71 ms (17.73 vs 6.02).
- Проигрыш по RPS — rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=14: ×0.80 (36146 vs 45022).
- Проигрыш по p99 — rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn, workers=14: +12.97 ms (17.73 vs 4.76).
