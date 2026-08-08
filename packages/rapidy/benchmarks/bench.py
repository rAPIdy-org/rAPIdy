from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

HOST, PORT = '127.0.0.1', 8000
BASE_URL = f'http://{HOST}:{PORT}'
REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_ROOT = REPO_ROOT / 'benchmarks'

STAND_ORDER = ['rapidy2-granian', 'rapidy2-uvicorn', 'fastapi-uvicorn', 'rapidy1-aiohttp']
PACKAGE_NAMES = ('rapidy', 'granian', 'uvicorn', 'fastapi', 'aiohttp', 'pydantic', 'gunicorn')


def venv_bin(stand: str) -> Path:
    return REPO_ROOT / '.venv-bench' / stand / 'bin'


def build_server_cmd(stand: str, workers: int) -> list[str]:
    binary_dir = venv_bin(stand)
    if stand == 'rapidy2-granian':
        return [
            str(binary_dir / 'granian'),
            '--interface',
            'asgi',
            '--host',
            HOST,
            '--port',
            str(PORT),
            '--workers',
            str(workers),
            'benchmarks.apps.app_rapidy2:app',
        ]
    if stand in {'rapidy2-uvicorn', 'fastapi-uvicorn'}:
        app = 'benchmarks.apps.app_rapidy2:app' if stand == 'rapidy2-uvicorn' else 'benchmarks.apps.app_fastapi:app'
        return [
            str(binary_dir / 'uvicorn'),
            app,
            '--host',
            HOST,
            '--port',
            str(PORT),
            '--workers',
            str(workers),
            '--loop',
            'uvloop',
            '--http',
            'httptools',
            '--no-access-log',
        ]
    if stand == 'rapidy1-aiohttp':
        if workers == 1:
            return [str(binary_dir / 'python'), '-m', 'benchmarks.apps.app_rapidy1']
        return [
            str(binary_dir / 'gunicorn'),
            'benchmarks.apps.app_rapidy1:app',
            '--worker-class',
            'aiohttp.GunicornWebWorker',
            '--workers',
            str(workers),
            '--bind',
            f'{HOST}:{PORT}',
        ]
    raise ValueError(f'unknown stand: {stand}')


def server_import_root(stand: str) -> Path:
    if stand != 'rapidy1-aiohttp':
        return REPO_ROOT
    import_root = REPO_ROOT / '.venv-bench' / stand / 'import-root'
    import_root.mkdir(parents=True, exist_ok=True)
    benchmarks_link = import_root / 'benchmarks'
    if not benchmarks_link.exists():
        benchmarks_link.symlink_to(BENCHMARKS_ROOT, target_is_directory=True)
    return import_root


def start_server(stand: str, workers: int) -> subprocess.Popen[str]:
    import_root = server_import_root(stand)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(import_root)
    return subprocess.Popen(
        build_server_cmd(stand, workers),
        cwd=import_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def process_diagnostics(proc: subprocess.Popen[str]) -> str:
    if proc.poll() is None:
        return ''
    stdout, stderr = proc.communicate()
    return '\n'.join(part for part in (stdout.strip(), stderr.strip()) if part)


def wait_ready(proc: subprocess.Popen[str], timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            details = process_diagnostics(proc)
            raise RuntimeError(f'server exited before readiness (code {proc.returncode})\n{details}')
        try:
            with urllib.request.urlopen(f'{BASE_URL}/health', timeout=1.0) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f'server did not become ready in {timeout_s:.0f}s')


def stop_server(proc: subprocess.Popen[str], timeout_s: float = 10.0) -> None:
    if proc.poll() is not None:
        proc.communicate()
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=timeout_s)
    proc.communicate()


def wait_port_free(timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.2):
                pass
        except OSError:
            return
        time.sleep(0.2)
    raise RuntimeError(f'{HOST}:{PORT} is still in use')


def http_request(path: str, payload: bytes | None = None) -> tuple[int, bytes]:
    headers = {'Content-Type': 'application/json'} if payload is not None else {}
    request = urllib.request.Request(f'{BASE_URL}{path}', data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def smoke_stand(stand: str) -> dict[str, Any]:
    valid = (BENCHMARKS_ROOT / 'common/payload.json').read_bytes()
    invalid = (BENCHMARKS_ROOT / 'common/payload_invalid.json').read_bytes()
    expected = {**json.loads(valid), 'processed': True}
    proc = start_server(stand, 1)
    try:
        wait_ready(proc)
        valid_status, valid_body = http_request('/users', valid)
        invalid_status, _ = http_request('/users', invalid)
        health_status, _ = http_request('/health')
        if valid_status != 200:
            raise RuntimeError(f'{stand}: valid request returned {valid_status}: {valid_body!r}')
        actual = json.loads(valid_body)
        if actual != expected:
            raise RuntimeError(f'{stand}: unexpected response: {actual!r}; expected {expected!r}')
        if invalid_status != 422:
            raise RuntimeError(f'{stand}: invalid request returned {invalid_status}, expected 422')
        if health_status != 200:
            raise RuntimeError(f'{stand}: health returned {health_status}, expected 200')
        print(f'{stand}: 200 valid / 422 invalid / health ok', flush=True)
        return actual
    finally:
        stop_server(proc)
        wait_port_free()


def parse_bombardier_output(stdout: str) -> dict[str, float | int]:
    start = stdout.find('{')
    if start < 0:
        raise RuntimeError(f'bombardier returned no JSON: {stdout[-1000:]}')
    try:
        payload, _ = json.JSONDecoder().raw_decode(stdout[start:])
        result = payload.get('result', payload)
        rps_value = result['rps']
        rps = float(rps_value['mean'] if isinstance(rps_value, dict) else rps_value)
        latency = result.get('latencies', result.get('latency'))
        percentiles = latency['percentiles']
        p50_ms = float(percentiles.get('50', percentiles.get('50.0'))) / 1000
        p95_ms = float(percentiles.get('95', percentiles.get('95.0'))) / 1000
        p99_ms = float(percentiles.get('99', percentiles.get('99.0'))) / 1000
        req2xx = int(result.get('req2xx', 0))
        non2xx = sum(int(result.get(name, 0)) for name in ('req1xx', 'req3xx', 'req4xx', 'req5xx', 'others'))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f'unsupported bombardier JSON: {payload!r}') from exc
    return {
        'rps': rps,
        'p50_ms': p50_ms,
        'p95_ms': p95_ms,
        'p99_ms': p99_ms,
        'req2xx': req2xx,
        'non2xx': non2xx,
    }


def validate_run(result: dict[str, float | int], diagnostic: str) -> dict[str, float | int]:
    if result['req2xx'] == 0 or result['non2xx'] > 0:
        raise RuntimeError(f'invalid load run: {result!r}\n{diagnostic[-1000:]}')
    return result


def run_bombardier(concurrency: int, duration_s: int) -> dict[str, float | int]:
    binary = shutil.which('bombardier')
    if binary is None:
        raise RuntimeError('bombardier is not installed')
    cmd = [
        binary,
        '-c',
        str(concurrency),
        '-d',
        f'{duration_s}s',
        '-m',
        'POST',
        '-H',
        'Content-Type: application/json',
        '-f',
        str(BENCHMARKS_ROOT / 'common/payload.json'),
        '--latencies',
        '--print',
        'r',
        '--format',
        'json',
        f'{BASE_URL}/users',
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=duration_s + 30)
    if completed.returncode != 0:
        raise RuntimeError(f'bombardier failed ({completed.returncode}): {completed.stderr[-2000:]}')
    return validate_run(parse_bombardier_output(completed.stdout), completed.stderr)


def run_wrk(concurrency: int, duration_s: int) -> dict[str, float | int]:
    binary = shutil.which('wrk')
    if binary is None:
        raise RuntimeError('wrk is not installed')
    threads = min(os.cpu_count() or 1, concurrency)
    cmd = [
        binary,
        f'-t{threads}',
        f'-c{concurrency}',
        f'-d{duration_s}s',
        '-s',
        str(BENCHMARKS_ROOT / 'wrk/post.lua'),
        '--latency',
        f'{BASE_URL}/users',
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=duration_s + 30)
    if completed.returncode != 0:
        raise RuntimeError(f'wrk failed ({completed.returncode}): {completed.stderr[-2000:]}')
    marker = 'BENCH_JSON '
    line = next((line for line in completed.stdout.splitlines() if marker in line), None)
    if line is None:
        raise RuntimeError(f'wrk returned no BENCH_JSON marker: {completed.stdout[-1000:]}')
    return validate_run(json.loads(line.split(marker, 1)[1]), completed.stderr)


def command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or completed.stderr).strip() or None


def tool_version(tool: str) -> str:
    binary = shutil.which(tool)
    if binary is None:
        return 'unknown'
    for flag in ('--version', '-v'):
        output = command_output([binary, flag])
        if output:
            return output.splitlines()[0]
    return 'unknown'


def package_versions(stand: str) -> dict[str, str]:
    script = (
        'import importlib.metadata,json; '
        f'names={PACKAGE_NAMES!r}; '
        'versions={}; '
        '\nfor name in names:\n'
        ' try: versions[name]=importlib.metadata.version(name)\n'
        ' except importlib.metadata.PackageNotFoundError: pass\n'
        'print(json.dumps(versions, sort_keys=True))'
    )
    output = command_output([str(venv_bin(stand) / 'python'), '-c', script])
    if output is None:
        raise RuntimeError(f'cannot collect package versions for {stand}')
    return json.loads(output)


def system_value(name: str) -> str | None:
    if platform.system() != 'Darwin':
        return None
    return command_output(['sysctl', '-n', name])


def ram_gb() -> float | None:
    darwin_bytes = system_value('hw.memsize')
    if darwin_bytes:
        return int(darwin_bytes) / 1024**3
    try:
        return os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 1024**3
    except (AttributeError, OSError, ValueError):
        return None


def collect_env(stand: str) -> dict[str, Any]:
    python = command_output([str(venv_bin(stand) / 'python'), '--version'])
    return {
        'python': python or 'unknown',
        'os': platform.platform(),
        'cpu': system_value('machdep.cpu.brand_string') or platform.processor() or 'unknown',
        'cpu_count': os.cpu_count(),
        'ram_gb': ram_gb(),
        'packages': package_versions(stand),
    }


def git_description() -> str | None:
    return command_output(['git', 'describe', '--always', '--dirty'])


def select_tool(requested: str) -> str:
    if requested == 'auto':
        for candidate in ('bombardier', 'wrk'):
            if shutil.which(candidate):
                return candidate
        raise RuntimeError('neither bombardier nor wrk is installed')
    if shutil.which(requested) is None:
        raise RuntimeError(f'{requested} is not installed')
    return requested


def run_load(tool: str, concurrency: int, duration_s: int) -> dict[str, float | int]:
    if tool == 'bombardier':
        return run_bombardier(concurrency, duration_s)
    return run_wrk(concurrency, duration_s)


def bench_cell(stand: str, workers: int, args: argparse.Namespace, tool: str) -> Path:
    proc = start_server(stand, workers)
    try:
        wait_ready(proc)
        print(f'{stand} w={workers}: warmup {args.warmup}s', flush=True)
        run_load(tool, args.concurrency, args.warmup)
        runs = []
        for repeat in range(1, args.repeats + 1):
            print(f'{stand} w={workers}: run {repeat}/{args.repeats} ({args.duration}s)', flush=True)
            runs.append(run_load(tool, args.concurrency, args.duration))
        metric_names = ('rps', 'p50_ms', 'p95_ms', 'p99_ms')
        medians = {name: statistics.median(float(run[name]) for run in runs) for name in metric_names}
        rps_values = [float(run['rps']) for run in runs]
        mean_rps = statistics.mean(rps_values)
        cv_rps = statistics.pstdev(rps_values) / mean_rps if len(rps_values) > 1 and mean_rps else 0.0
        timestamp = datetime.now().isoformat(timespec='seconds')
        raw = {
            'stand': stand,
            'workers': workers,
            'concurrency': args.concurrency,
            'duration_s': args.duration,
            'warmup_s': args.warmup,
            'repeats': args.repeats,
            'tool': tool,
            'tool_version': tool_version(tool),
            'timestamp': timestamp,
            'git': git_description(),
            'env': collect_env(stand),
            'runs': runs,
            'median': medians,
            'cv_rps': cv_rps,
            'unstable': cv_rps > 0.10,
        }
        stamp = datetime.fromisoformat(timestamp).strftime('%Y%m%dT%H%M%S')
        output = BENCHMARKS_ROOT / 'results/raw' / f'{stand}-w{workers}-c{args.concurrency}-{stamp}.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(
            f'{stand} w={workers}: RPS={medians["rps"]:.0f} p99={medians["p99_ms"]:.2f}ms cv={cv_rps:.1%}',
            flush=True,
        )
        return output
    finally:
        stop_server(proc)
        wait_port_free()


def parse_workers(value: str) -> list[int]:
    workers = []
    for raw_token in value.split(','):
        token = raw_token.strip()
        count = (os.cpu_count() or 1) if token.upper() == 'NPROC' else int(token)
        if count < 1:
            raise argparse.ArgumentTypeError('worker counts must be positive')
        if count not in workers:
            workers.append(count)
    if not workers:
        raise argparse.ArgumentTypeError('at least one worker count is required')
    return workers


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('value must be positive')
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run reproducible rAPIdy benchmark stands.')
    parser.add_argument('--stand', choices=[*STAND_ORDER, 'all'], required=True)
    parser.add_argument('--workers', type=parse_workers, default=parse_workers('1,NPROC'))
    parser.add_argument('--concurrency', type=positive_int, default=128)
    parser.add_argument('--duration', type=positive_int, default=30)
    parser.add_argument('--repeats', type=positive_int, default=3)
    parser.add_argument('--warmup', type=positive_int, default=5)
    parser.add_argument('--tool', choices=('auto', 'bombardier', 'wrk'), default='auto')
    parser.add_argument('--smoke', action='store_true')
    return parser.parse_args(argv)


def check_venvs(stands: list[str]) -> None:
    missing = [stand for stand in stands if not (venv_bin(stand) / 'python').is_file()]
    if missing:
        names = ', '.join(missing)
        raise RuntimeError(f'missing benchmark venvs: {names}; create them using benchmarks/README.md')


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stands = STAND_ORDER if args.stand == 'all' else [args.stand]
    try:
        check_venvs(stands)
        wait_port_free()
        if args.smoke:
            responses = [smoke_stand(stand) for stand in stands]
            if args.stand == 'all':
                if any(response != responses[0] for response in responses[1:]):
                    raise RuntimeError(f'responses differ across stands: {responses!r}')
                print('responses identical across 4 stands')
            return 0
        tool = select_tool(args.tool)
        print(f'load tool: {tool} ({tool_version(tool)})', flush=True)
        for stand in stands:
            for workers in args.workers:
                bench_cell(stand, workers, args, tool)
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f'benchmark failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
