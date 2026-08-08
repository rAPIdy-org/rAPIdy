from __future__ import annotations

import argparse
from collections.abc import Sequence

from rapidy.serve import run_app


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog='python -m rapidy')
    parser.add_argument('target', help="ASGI target in 'module:attribute' form")
    parser.add_argument('--host', default='0.0.0.0')  # noqa: S104
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--workers-kill-timeout', type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI with an optional explicit argv."""
    args = build_parser().parse_args(argv)
    run_app(
        args.target,
        host=args.host,
        port=args.port,
        workers=args.workers,
        workers_kill_timeout=args.workers_kill_timeout,
    )


if __name__ == '__main__':
    main()
