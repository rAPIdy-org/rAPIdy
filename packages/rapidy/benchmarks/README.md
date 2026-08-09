# rAPIdy benchmark matrix

Этот каталог воспроизводит сравнение четырёх стендов: rAPIdy 2.0 с Granian, rAPIdy 2.0 с
Uvicorn, FastAPI с Uvicorn и rAPIdy 1.1.2 с aiohttp. Нужны Python 3.12 или новее и
`bombardier`; `wrk` поддерживается только как fallback. Точная версия инструмента записывается
в `RESULTS.md`.

Перед измерением подключите питание, включите performance-режим и закройте браузер, IDE,
индексаторы и другие фоновые нагрузки. Shared CI для численного сравнения не подходит.
Генератор нагрузки работает на той же машине и отнимает CPU, поэтому многоворкерные результаты
консервативны. При необходимости генератор можно перенести на другую машину, изменив host в
`bench.py`, но эталонная матрица запускается локально.

## Установка с нуля

Из корня пакета `packages/rapidy` выполните:

```bash
for stand in rapidy2-granian rapidy2-uvicorn fastapi-uvicorn rapidy1-aiohttp; do
  python3.12 -m venv .venv-bench/$stand
  .venv-bench/$stand/bin/pip install -r benchmarks/requirements/$stand.txt
done
.venv-bench/rapidy2-granian/bin/pip install -e ../rapidy_core
.venv-bench/rapidy2-uvicorn/bin/pip install -e ../rapidy_core
.venv-bench/rapidy2-granian/bin/pip install -e '.[granian]'
.venv-bench/rapidy2-uvicorn/bin/pip install -e '.[uvicorn]'
brew install bombardier
python3.12 benchmarks/bench.py --stand all --smoke
python3.12 benchmarks/bench.py --stand all --workers 1,$(python3.12 -c 'import os;print(os.cpu_count())') --duration 30 --repeats 3
python3.12 benchmarks/report.py
```

Вместо Homebrew можно установить инструмент командой
`go install github.com/codesenberg/bombardier@latest`. Если доступен только `wrk`, передайте
`--tool wrk`; Lua-сценарий находится в `benchmarks/wrk/post.lua`, и команду следует запускать
строго из корня пакета. Не смешивайте raw-файлы разных инструментов в одном отчёте.

Smoke проверяет на каждом стенде валидный ответ 200, ошибку валидации 422 и health endpoint,
а затем сравнивает JSON-ответы. Полный запуск создаёт сырые данные в
`benchmarks/results/raw/*.json`; `report.py` выбирает последнюю запись каждой ячейки и полностью
перегенерирует `benchmarks/RESULTS.md`.

Локальная установка `../rapidy_core` обязательна до его отдельной публикации на PyPI; это
сохраняет benchmark-процесс полностью локальным и не требует релиза пакетов.

Таблицы разделены по числу workers. Значения — медианы трёх повторов; CV показывает разброс
RPS, а `*` отмечает CV выше 10%. В выводах приведены численные отношения RPS и дельты p99.

## Почему четыре venv

rAPIdy 1.x и 2.0 имеют одно PyPI-имя `rapidy` и не могут одновременно находиться в одном
окружении. Поэтому каждый стенд обязан использовать собственный `.venv-bench/<stand>`.
Это также не позволяет зависимостям FastAPI, aiohttp и gunicorn попасть в пакет rAPIdy 2.0.
Для legacy-процесса `bench.py` создаёт изолированный import-root со ссылкой только на
`benchmarks/`, иначе локальный каталог исходников 2.0 затенил бы установленный пакет 1.1.2.

## Compression microbenchmark

Отдельный transport-level microbenchmark проверяет round-trip, размер wire body и median cost для identity, gzip и
установленного optional Brotli на одном и том же 64 KiB JSON payload:

```bash
uv run --group test python packages/rapidy/tests/perf/bench_compression.py --iterations 500
```

Числа предназначены для сравнения изменений на одной машине, а не для межмашинного performance gate.
