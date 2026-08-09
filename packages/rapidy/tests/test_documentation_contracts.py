from __future__ import annotations

import ast
import importlib
import re
import textwrap
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
RELATIVE_MARKDOWN_LINK = re.compile(r'\]\((?!https://|#|mailto:)[^)]+\)')
LOCAL_DOC_MODULES = {'main'}
LEGACY_MARKER = '<!-- RAPIDY_LEGACY_1X -->'
LEGACY_DIRECTORIES = ('about', 'aiohttp_migration', 'docs', 'examples', 'why')


def _published_markdown_files() -> tuple[Path, ...]:
    docs_root = PACKAGE_ROOT / 'docs' / 'docs'
    paths: list[Path] = []
    for language in ('en', 'ru'):
        language_root = docs_root / language
        paths.extend((language_root / 'index.md', language_root / 'quickstart' / 'index.md'))
        paths.extend(sorted((language_root / 'guide').glob('*.md')))
    return tuple(paths)


def _legacy_markdown_files() -> tuple[Path, ...]:
    docs_root = PACKAGE_ROOT / 'docs' / 'docs'
    paths: list[Path] = []
    for language in ('en', 'ru'):
        language_root = docs_root / language
        paths.append(language_root / 'home.md')
        for directory in LEGACY_DIRECTORIES:
            paths.extend(sorted((language_root / directory).rglob('*.md')))
    return tuple(paths)


def _python_blocks(path: Path) -> Iterator[tuple[int, str]]:
    start_line: int | None = None
    block: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        if start_line is None:
            if line.strip() == '```python':
                start_line = line_number + 1
            continue
        if line.strip() == '```':
            yield start_line, textwrap.dedent('\n'.join(block))
            start_line = None
            block = []
            continue
        block.append(line)
    assert start_line is None, f'{path}: unterminated Python code fence'


def test_distribution_readmes_use_pypi_safe_links() -> None:
    readmes = (
        PACKAGE_ROOT / 'README.md',
        PACKAGE_ROOT.parent / 'rapidy_client' / 'README.md',
    )

    for readme in readmes:
        assert RELATIVE_MARKDOWN_LINK.findall(readme.read_text(encoding='utf-8')) == []


def test_migration_guide_matches_application_compatibility_contract() -> None:
    migration = (REPOSITORY_ROOT / 'MIGRATION.md').read_text(encoding='utf-8')

    assert 'middleware=[add_headers]' not in migration
    assert 'middlewares=[add_headers]' in migration
    assert '`logger` and `handler_args` remain accepted' in migration


def test_published_guide_files_have_language_parity() -> None:
    docs_root = PACKAGE_ROOT / 'docs' / 'docs'
    english = {path.name for path in (docs_root / 'en' / 'guide').glob('*.md')}
    russian = {path.name for path in (docs_root / 'ru' / 'guide').glob('*.md')}

    assert english == russian


def test_every_excluded_legacy_page_has_an_unambiguous_1x_banner() -> None:
    legacy_files = _legacy_markdown_files()

    assert len(legacy_files) >= 70
    assert all(LEGACY_MARKER in path.read_text(encoding='utf-8') for path in legacy_files)
    assert all(
        LEGACY_MARKER not in path.read_text(encoding='utf-8')
        for path in _published_markdown_files()
    )


def test_quickstarts_use_the_cli_default_port() -> None:
    docs_root = PACKAGE_ROOT / 'docs' / 'docs'

    for language in ('en', 'ru'):
        quickstart = (docs_root / language / 'quickstart' / 'index.md').read_text(encoding='utf-8')
        assert 'curl http://127.0.0.1:8080/' in quickstart
        assert 'curl http://127.0.0.1:8000/' not in quickstart


def test_published_python_snippets_compile_and_resolve_public_imports() -> None:
    checked_blocks = 0
    for path in _published_markdown_files():
        assert path.is_file()
        for line_number, source in _python_blocks(path):
            label = f'{path.relative_to(REPOSITORY_ROOT)}:{line_number}'
            tree = ast.parse(source, filename=label)
            checked_blocks += 1
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        importlib.import_module(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module not in LOCAL_DOC_MODULES:
                    assert node.module is not None, f'{label}: relative imports are not executable documentation'
                    module = importlib.import_module(node.module)
                    for alias in node.names:
                        assert alias.name == '*' or hasattr(module, alias.name), (
                            f'{label}: {node.module}.{alias.name} is not importable'
                        )

    assert checked_blocks >= 50
