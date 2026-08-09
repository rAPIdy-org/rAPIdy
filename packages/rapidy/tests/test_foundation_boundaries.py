from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
import tomllib
from pathlib import Path
from typing import Any

import rapidy
from rapidy import background, middlewares, security, testing
from rapidy.middlewares import compression, proxy_headers
from rapidy.security import schemes
from rapidy.testing import client as testing_client

PACKAGE_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PACKAGE_ROOT / 'rapidy'

EXPECTED_DEPENDENCIES = {
    'pydantic>=2.9,<3',
    'rapidy-core>=0.1,<0.2',
    'multidict>=6,<7',
    'python-multipart>=0.0.20,<1',
}
EXPECTED_EXTRAS = {
    'brotli': ['brotli>=1.1,<2'],
    'granian': ['granian>=2.7,<3'],
    'otel': [
        'opentelemetry-api>=1.44,<2',
        'opentelemetry-instrumentation-asgi>=0.65b0,<1',
    ],
    'uvicorn': ['uvicorn[standard]>=0.34,<1'],
    'hypercorn': ['hypercorn>=0.17,<1'],
    'test': ['anyio>=4,<5', 'httpx>=0.28,<1'],
}
FORBIDDEN_SOURCE_PATHS = {
    '_client_errors.py',
    'annotation_checkers.py',
    'encoders.py',
    'enums.py',
    'fields',
    'mypy',
    'parameters',
}
FORBIDDEN_IMPORT_ROOTS = {'aiohttp', 'dishka', 'rapidy_client'}


def _public_class_members(exported_class: type[Any]) -> list[tuple[str, Any]]:
    targets: list[tuple[str, Any]] = []
    for name, raw_member in vars(exported_class).items():
        if name.startswith('_'):
            continue
        if isinstance(raw_member, (staticmethod, classmethod)):
            members = (raw_member.__func__,)
        elif isinstance(raw_member, property):
            accessors = (raw_member.fget, raw_member.fset, raw_member.fdel)
            members = tuple(item for item in accessors if item is not None)
        elif callable(raw_member):
            members = (raw_member,)
        else:
            members = ()
        label = f'{exported_class.__module__}.{exported_class.__qualname__}.{name}'
        targets.extend((label, item) for item in members)
    return targets


def _public_signature_targets() -> list[tuple[str, Any]]:
    callables: dict[int, Any] = {}
    classes: dict[int, type[Any]] = {}
    for module_info in pkgutil.walk_packages(rapidy.__path__, f'{rapidy.__name__}.'):
        module = importlib.import_module(module_info.name)
        for name in getattr(module, '__all__', ()):
            exported = getattr(module, name)
            if not callable(exported) or not getattr(exported, '__module__', '').startswith('rapidy'):
                continue
            callables[id(exported)] = exported
            if inspect.isclass(exported):
                classes[id(exported)] = exported

    targets = [(f'{item.__module__}.{item.__qualname__}', item) for item in callables.values()]
    for exported_class in classes.values():
        targets.extend(_public_class_members(exported_class))
    return targets


def test_server_manifest_has_frozen_foundation_dependencies() -> None:
    with (PACKAGE_ROOT / 'pyproject.toml').open('rb') as manifest_file:
        project = tomllib.load(manifest_file)['project']

    assert project['version'] == '2.0.0'
    assert project['requires-python'] == '>=3.12'
    assert set(project['dependencies']) == EXPECTED_DEPENDENCIES
    assert project['optional-dependencies'] == EXPECTED_EXTRAS


def test_server_source_has_no_core_copies_or_cross_package_imports() -> None:
    present_source_paths = {
        path.name
        for path in SOURCE_ROOT.iterdir()
        if path.is_file() or any(path.rglob('*.py'))
    }
    assert present_source_paths.isdisjoint(FORBIDDEN_SOURCE_PATHS)

    imported_roots: set[str] = set()
    for source_file in SOURCE_ROOT.rglob('*.py'):
        tree = ast.parse(source_file.read_text(), filename=source_file)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.partition('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.partition('.')[0])

    assert imported_roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS)


def test_consumers_do_not_import_private_core_names() -> None:
    violations: list[str] = []
    consumer_roots = (SOURCE_ROOT, PACKAGE_ROOT.parent / 'rapidy_client' / 'rapidy_client')

    for consumer_root in consumer_roots:
        for source_file in consumer_root.rglob('*.py'):
            tree = ast.parse(source_file.read_text(), filename=source_file)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                if node.module == 'rapidy_core' or node.module.startswith('rapidy_core.'):
                    for imported_name in node.names:
                        if imported_name.name.startswith('_'):
                            relative_path = source_file.relative_to(PACKAGE_ROOT.parent)
                            violations.append(f'{relative_path}:{node.lineno}:{imported_name.name}')

    assert violations == []


def test_types_used_by_public_signatures_are_exported_by_their_facades() -> None:
    expected_exports = (
        (background, ('Background', 'BackgroundCallable', 'BackgroundRunner')),
        (compression, ('CompressionAlgorithm',)),
        (middlewares, ('CompressionAlgorithm', 'ProxyHeaderMode')),
        (proxy_headers, ('ProxyHeaderMode',)),
        (schemes, ('AuthResult', 'AuthVerifier')),
        (security, ('AuthResult', 'AuthVerifier')),
        (testing_client, ('ClientAddress',)),
        (testing, ('ClientAddress',)),
    )

    for module, names in expected_exports:
        assert set(names) <= set(module.__all__)
        assert all(getattr(module, name) is not None for name in names)

    assert middlewares.CompressionAlgorithm is compression.CompressionAlgorithm
    assert middlewares.ProxyHeaderMode is proxy_headers.ProxyHeaderMode
    assert security.AuthResult is schemes.AuthResult
    assert security.AuthVerifier is schemes.AuthVerifier
    assert testing.ClientAddress is testing_client.ClientAddress


def test_all_public_runtime_annotations_resolve() -> None:
    failures: list[str] = []
    checked = 0
    for label, target in _public_signature_targets():
        try:
            inspect.signature(target, eval_str=True)
        except (TypeError, ValueError):
            continue
        except Exception as exc:
            failures.append(f'{label}: {type(exc).__name__}: {exc}')
        else:
            checked += 1

    assert checked >= 380
    assert failures == []
