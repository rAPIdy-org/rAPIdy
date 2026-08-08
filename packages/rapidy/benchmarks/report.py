from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BENCHMARKS_ROOT = Path(__file__).resolve().parent
RAW_ROOT = BENCHMARKS_ROOT / 'results/raw'
RESULTS_PATH = BENCHMARKS_ROOT / 'RESULTS.md'
STAND_ORDER = ['rapidy2-granian', 'rapidy2-uvicorn', 'fastapi-uvicorn', 'rapidy1-aiohttp']

COMPARISONS = (
    ('fastapi-uvicorn', 'rAPIdy 2.0+Granian vs FastAPI+uvicorn'),
    ('rapidy1-aiohttp', 'rAPIdy 2.0+Granian vs rAPIdy 1.x (aiohttp)'),
    ('rapidy2-uvicorn', 'rAPIdy 2.0+Granian vs rAPIdy 2.0+uvicorn'),
)


def load_latest_cells(raw_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    cells: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(raw_dir.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        key = (data['stand'], int(data['workers']))
        if key not in cells or data['timestamp'] > cells[key]['timestamp']:
            cells[key] = data
    return cells


def format_packages(cells: dict[tuple[str, int], dict[str, Any]]) -> list[str]:
    lines = ['Версии пакетов по стендам:']
    for stand in STAND_ORDER:
        stand_cells = [cell for (name, _), cell in cells.items() if name == stand]
        if not stand_cells:
            continue
        cell = max(stand_cells, key=lambda item: item['timestamp'])
        packages = cell['env'].get('packages', {})
        rendered = ', '.join(f'`{name}=={version}`' for name, version in sorted(packages.items()))
        lines.append(f'- `{stand}`: {rendered}')
    return lines


def comparison_rows(cells: dict[tuple[str, int], dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for workers in sorted({workers for _, workers in cells}):
        granian = cells.get(('rapidy2-granian', workers))
        if granian is None:
            continue
        for other_stand, label in COMPARISONS:
            other = cells.get((other_stand, workers))
            if other is None:
                continue
            granian_rps = float(granian['median']['rps'])
            other_rps = float(other['median']['rps'])
            granian_p99 = float(granian['median']['p99_ms'])
            other_p99 = float(other['median']['p99_ms'])
            rows.append(
                {
                    'workers': workers,
                    'label': label,
                    'ratio': granian_rps / other_rps,
                    'rps_a': granian_rps,
                    'rps_b': other_rps,
                    'delta': granian_p99 - other_p99,
                    'p99_a': granian_p99,
                    'p99_b': other_p99,
                }
            )
    return rows


def render_values(values: list[int]) -> str:
    return ','.join(str(value) for value in values)


def render_results(cells: dict[tuple[str, int], dict[str, Any]]) -> str:
    if not cells:
        raise ValueError(f'no raw benchmark files found in {RAW_ROOT}')
    tools = {cell['tool'] for cell in cells.values()}
    if len(tools) != 1:
        raise ValueError(f'raw matrix mixes load tools: {sorted(tools)}')
    latest = max(cells.values(), key=lambda item: item['timestamp'])
    env = latest['env']
    ram = env.get('ram_gb')
    ram_text = f'{ram:.1f} GiB' if isinstance(ram, (int, float)) else 'unknown'
    tool = latest['tool']
    versions = sorted({cell['tool_version'] for cell in cells.values()})
    tool_versions = '; '.join(versions)
    concurrency = sorted({int(cell['concurrency']) for cell in cells.values()})
    durations = sorted({int(cell['duration_s']) for cell in cells.values()})
    warmups = sorted({int(cell['warmup_s']) for cell in cells.values()})
    repeats = sorted({int(cell['repeats']) for cell in cells.values()})

    lines = [
        '# rAPIdy 2.0 — результаты бенчмарков',
        '',
        'Сгенерировано `benchmarks/report.py` из `benchmarks/results/raw/`; вручную не редактировать.',
        '',
        '## Окружение',
        '',
        f'- Дата последнего замера: `{latest["timestamp"]}`.',
        f'- CPU: {env.get("cpu", "unknown")} ({env.get("cpu_count", "unknown")} логических ядер).',
        f'- RAM: {ram_text}.',
        f'- ОС: `{env.get("os", "unknown")}`.',
        f'- Python: `{env.get("python", "unknown")}`.',
        f'- Инструмент нагрузки: `{tool}` — `{tool_versions}`.',
        '',
        *format_packages(cells),
        '',
        '## Методика',
        '',
        'Во всех стендах один сценарий: `POST /users` принимает `UserIn`, валидирует JSON и возвращает '
        '`UserOut` с `processed=true`. Приложения находятся в `benchmarks/apps/app_rapidy2.py`, '
        '`benchmarks/apps/app_fastapi.py` и `benchmarks/apps/app_rapidy1.py`; общие модели — в '
        '`benchmarks/common/models.py`, payload — в `benchmarks/common/payload.json`.',
        '',
        f'Нагрузка: concurrency={render_values(concurrency)}, duration={render_values(durations)} s, '
        f'warmup={render_values(warmups)} s; итог — медиана из {render_values(repeats)} повторов. '
        'Генератор нагрузки работает на той же машине, поэтому многоворкерные числа '
        'консервативны. Каждый стенд использует отдельный `.venv-bench/<stand>`: PyPI-пакеты rAPIdy 1.x и '
        '2.0 одноимённы. Версия pydantic одинакова во всех окружениях.',
        '',
        'Вход и выход валидируются штатными средствами: `response_validate=True` у rAPIdy 2.0 и rAPIdy 1.x, '
        '`response_model` у FastAPI. Access-log выключен. Uvicorn всегда запускается с `--loop uvloop '
        '--http httptools`. Для rAPIdy 1.x при workers > 1 используется gunicorn + '
        '`aiohttp.GunicornWebWorker`; из-за другого process manager эта таблица частично сравнивает '
        '«яблоки с грушами», тогда как workers=1 — чистое сравнение одного процесса. Абсолютные числа '
        'сопоставимы только внутри одной таблицы.',
        '',
    ]

    for workers in sorted({workers for _, workers in cells}):
        lines.extend(
            [
                f'### workers = {workers}',
                '',
                '| Стенд | RPS | p50, ms | p95, ms | p99, ms | CV |',
                '|---|---:|---:|---:|---:|---:|',
            ]
        )
        unstable = False
        for stand in STAND_ORDER:
            cell = cells.get((stand, workers))
            if cell is None:
                continue
            median = cell['median']
            marker = '*' if cell['unstable'] else ''
            unstable = unstable or bool(cell['unstable'])
            lines.append(
                f'| {stand} | {median["rps"]:.0f} | {median["p50_ms"]:.2f} | '
                f'{median["p95_ms"]:.2f} | {median["p99_ms"]:.2f} | {cell["cv_rps"]:.1%}{marker} |'
            )
        lines.append('')
        if unstable:
            lines.extend([r'\* CV > 10% — прогон нестабилен, интерпретировать с осторожностью.', ''])

    comparisons = comparison_rows(cells)
    lines.extend(['## Выводы', ''])
    if comparisons:
        for row in comparisons:
            lines.append(
                f'- {row["label"]}, workers={row["workers"]}: RPS ×{row["ratio"]:.2f} '
                f'({row["rps_a"]:.0f} vs {row["rps_b"]:.0f}), p99 {row["delta"]:+.2f} ms '
                f'({row["p99_a"]:.2f} vs {row["p99_b"]:.2f}).'
            )
    else:
        lines.append('- Для численного сравнения пока недостаточно пар ячеек.')

    lines.extend(['', '### Где проигрываем / паритет', ''])
    classifications = []
    for row in comparisons:
        if row['ratio'] < 0.97:
            classifications.append(
                f'- Проигрыш по RPS — {row["label"]}, workers={row["workers"]}: ×{row["ratio"]:.2f} '
                f'({row["rps_a"]:.0f} vs {row["rps_b"]:.0f}).'
            )
        elif row['ratio'] <= 1.03:
            classifications.append(
                f'- Паритет по RPS — {row["label"]}, workers={row["workers"]}: ×{row["ratio"]:.2f} '
                f'({row["rps_a"]:.0f} vs {row["rps_b"]:.0f}).'
            )
        if row['delta'] > 0:
            classifications.append(
                f'- Проигрыш по p99 — {row["label"]}, workers={row["workers"]}: '
                f'{row["delta"]:+.2f} ms ({row["p99_a"]:.2f} vs {row["p99_b"]:.2f}).'
            )
    if classifications:
        lines.extend(classifications)
    elif comparisons:
        closest = min(comparisons, key=lambda item: abs(item['ratio'] - 1))
        lines.extend(
            [
                'На данной матрице проигрышей не зафиксировано.',
                f'- Ближайшая к паритету пара: {closest["label"]}, workers={closest["workers"]}, '
                f'RPS ×{closest["ratio"]:.2f} ({closest["rps_a"]:.0f} vs {closest["rps_b"]:.0f}).',
            ]
        )
    else:
        lines.append('Недостаточно пар ячеек для классификации проигрышей или паритета.')
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    try:
        cells = load_latest_cells(RAW_ROOT)
        RESULTS_PATH.write_text(render_results(cells), encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'report generation failed: {exc}', file=sys.stderr)
        return 1
    print(f'wrote {RESULTS_PATH.relative_to(BENCHMARKS_ROOT.parent)} from {len(cells)} cells')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
