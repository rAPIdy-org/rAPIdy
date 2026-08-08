from __future__ import annotations

import ast
import tomllib
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PACKAGE_ROOT / 'rapidy'

EXPECTED_DEPENDENCIES = {
    'pydantic>=2.9,<3',
    'rapidy-core>=0.1,<0.2',
    'multidict>=6,<7',
    'python-multipart>=0.0.20,<1',
}
EXPECTED_EXTRAS = {
    'granian': ['granian>=2.7,<3'],
    'uvicorn': ['uvicorn>=0.34,<1'],
    'hypercorn': ['hypercorn>=0.17,<1'],
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
