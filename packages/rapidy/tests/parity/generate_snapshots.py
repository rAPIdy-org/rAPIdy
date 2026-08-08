from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

REFERENCE_VERSION = '1.1.2'
WORKSPACE = Path(__file__).resolve().parents[4]
SNAPSHOTS = {
    'rapidy_1x_http_all.txt': 'rapidy/http.py',
    'rapidy_1x_depends_all.txt': 'rapidy/depends.py',
    'rapidy_1x_init_all.txt': 'rapidy/__init__.py',
}


def _reference_source(path: str) -> str:
    git = shutil.which('git')
    if git is None:
        msg = 'git executable is required to generate parity snapshots'
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - executable and reference paths are controlled constants.
        (git, '-C', str(WORKSPACE), 'show', f'1.x:{path}'),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _assigns_name(node: ast.stmt, name: str) -> bool:
    if isinstance(node, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name


def _literal_assignment(source: str, name: str) -> object:
    for node in ast.parse(source).body:
        if _assigns_name(node, name):
            assert isinstance(node, (ast.Assign, ast.AnnAssign))
            if node.value is not None:
                return ast.literal_eval(node.value)
    msg = f'{name} not found in reference source'
    raise RuntimeError(msg)


def _public_names(source: str) -> tuple[str, ...]:
    value = _literal_assignment(source, '__all__')
    if not isinstance(value, (list, tuple)) or not all(isinstance(name, str) for name in value):
        msg = 'reference __all__ must be a literal sequence of strings'
        raise TypeError(msg)
    return tuple(dict.fromkeys(value))


def main() -> None:
    init_source = _reference_source('rapidy/__init__.py')
    if _literal_assignment(init_source, '__version__') != REFERENCE_VERSION:
        msg = f'reference version must remain {REFERENCE_VERSION}'
        raise RuntimeError(msg)

    output_dir = Path(__file__).parent
    for filename, source_path in SNAPSHOTS.items():
        source = init_source if source_path == 'rapidy/__init__.py' else _reference_source(source_path)
        names = _public_names(source)
        (output_dir / filename).write_text(f"{'\n'.join(names)}\n", encoding='utf-8')


if __name__ == '__main__':
    main()
