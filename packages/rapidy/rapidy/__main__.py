from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rapidy.application import Rapidy
from rapidy.serve import MissingUvicornDependencyError, run_app


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog='rapidy')
    commands = parser.add_subparsers(dest='command', required=True)

    run_parser = commands.add_parser('run', help='run an application with Uvicorn')
    _add_server_arguments(run_parser, host='0.0.0.0')  # noqa: S104

    dev_parser = commands.add_parser('dev', help='run a development server')
    _add_server_arguments(dev_parser, host='127.0.0.1')
    dev_parser.add_argument('--reload', action=argparse.BooleanOptionalAction, default=True)

    routes_parser = commands.add_parser('routes', help='print registered HTTP routes')
    routes_parser.add_argument('target', help="application in 'module:attribute' form")
    _add_app_dir_argument(routes_parser)
    routes_parser.add_argument('--json', action='store_true', dest='as_json')

    check_parser = commands.add_parser('check', help='validate application configuration')
    check_parser.add_argument('target', help="application in 'module:attribute' form")
    _add_app_dir_argument(check_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI with an optional explicit argv."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Preserve ``python -m rapidy module:app`` from the 2.0 pre-release CLI.
    if arguments and arguments[0] not in {'run', 'dev', 'routes', 'check', '-h', '--help'}:
        arguments.insert(0, 'run')
    args = build_parser().parse_args(arguments)
    app_dir = _prepare_app_dir(args.app_dir)
    if args.command in {'run', 'dev'}:
        try:
            run_app(
                args.target,
                app_dir=app_dir,
                host=args.host,
                port=args.port,
                workers=args.workers,
                timeout_graceful_shutdown=args.timeout_graceful_shutdown,
                **({'reload': args.reload} if args.command == 'dev' else {}),
            )
        except MissingUvicornDependencyError as exc:
            raise SystemExit(str(exc)) from exc
        return

    app = load_app(args.target)
    if args.command == 'routes':
        _print_routes(app, as_json=args.as_json)
        return
    _check_app(app)


def load_app(target: str) -> Rapidy:
    """Import and validate one ``module:attribute`` target."""
    module_name, separator, attribute_path = target.partition(':')
    if not separator or not module_name or not attribute_path:
        msg = "Application target must use 'module:attribute' form"
        raise SystemExit(msg)
    try:
        value: Any = importlib.import_module(module_name)
        for attribute in attribute_path.split('.'):
            value = getattr(value, attribute)
    except (ImportError, AttributeError) as exc:
        msg = f'Cannot import application target {target!r}: {exc}'
        raise SystemExit(msg) from exc
    if not isinstance(value, Rapidy):
        msg = f'Application target {target!r} is not a Rapidy instance'
        raise SystemExit(msg)
    return value


def _add_server_arguments(parser: argparse.ArgumentParser, *, host: str) -> None:
    parser.add_argument('target', help="ASGI target in 'module:attribute' form")
    _add_app_dir_argument(parser)
    parser.add_argument('--host', default=host)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--timeout-graceful-shutdown', type=int)


def _add_app_dir_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--app-dir',
        default='.',
        help='directory containing the application module (default: current directory)',
    )


def _prepare_app_dir(value: str) -> str:
    app_dir = Path(value).resolve()
    if not app_dir.is_dir():
        msg = f'Application directory does not exist or is not a directory: {value!r}'
        raise SystemExit(msg)
    resolved = str(app_dir)
    if resolved in sys.path:
        sys.path.remove(resolved)
    sys.path.insert(0, resolved)
    return resolved


def _print_routes(app: Rapidy, *, as_json: bool) -> None:
    routes = [
        {
            'method': record.method,
            'path': record.path,
            'name': record.route_kwargs.get('name'),
            'auto_head': record.is_auto_head,
        }
        for record in app.routes
    ]
    if as_json:
        print(json.dumps(routes, indent=2, sort_keys=True))  # noqa: T201
        return
    print(f'{"METHOD":<8} {"PATH":<40} NAME')  # noqa: T201
    for route in routes:
        auto = ' (auto)' if route['auto_head'] else ''
        print(f'{route["method"]:<8} {route["path"]:<40} {route["name"] or "-"}{auto}')  # noqa: T201


def _check_app(app: Rapidy) -> None:
    named: dict[str, set[str]] = {}
    for record in app.routes:
        name = record.route_kwargs.get('name')
        if isinstance(name, str):
            named.setdefault(name, set()).add(record.path)
    ambiguous = sorted(name for name, paths in named.items() if len(paths) > 1)
    if ambiguous:
        msg = f'Ambiguous route names: {", ".join(ambiguous)}'
        raise SystemExit(msg)
    openapi = 'disabled'
    if app.openapi_config is not None:
        config = app.openapi_config
        try:
            _ = app.openapi_schema
        except Exception as exc:
            msg = f'OpenAPI schema validation failed: {exc}'
            raise SystemExit(msg) from exc
        openapi = ', '.join([config.json_path, *(plugin.path for plugin in config.get_render_plugins())])
    visible_routes = sum(not record.is_auto_head for record in app.routes)
    print(  # noqa: T201
        f'OK: routes={visible_routes}, named={len(named)}, mounts={len(app._subapps)}, openapi={openapi}'  # noqa: SLF001
    )


if __name__ == '__main__':
    main()
