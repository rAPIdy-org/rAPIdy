from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def wait_for_port(process: subprocess.Popen[bytes], port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            msg = f'Server exited early with code {process.returncode}'
            raise RuntimeError(msg)
        with socket.socket() as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                return
        time.sleep(0.05)
    msg = f'Server did not bind port {port}'
    raise TimeoutError(msg)


@contextmanager
def live_server(runtime: str, target: str) -> Iterator[str]:
    port = free_port()
    bin_dir = Path(sys.executable).parent
    if runtime == 'uvicorn':
        command = [
            str(bin_dir / 'uvicorn'),
            target,
            '--host',
            '127.0.0.1',
            '--port',
            str(port),
            '--log-level',
            'warning',
        ]
    elif runtime == 'granian':
        command = [
            str(bin_dir / 'granian'),
            '--interface',
            'asgi',
            '--host',
            '127.0.0.1',
            '--port',
            str(port),
            '--log-level',
            'warning',
            target,
        ]
    elif runtime == 'rapidy':
        command = [
            sys.executable,
            '-m',
            'rapidy',
            target,
            '--host',
            '127.0.0.1',
            '--port',
            str(port),
        ]
    else:
        raise ValueError(runtime)

    process = subprocess.Popen(  # noqa: S603
        command,
        cwd=Path(__file__).parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_port(process, port)
        yield f'http://127.0.0.1:{port}'
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
