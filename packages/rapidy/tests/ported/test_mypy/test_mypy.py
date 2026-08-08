from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
from mypy import api as mypy_api

ROOT_TESTS_MYPY_DIR: Final[Path] = Path(__file__).parent

DEFAULT_CONFIG_NAME: Final[str] = 'default_pyproject.toml'
STRICT_CONFIG_NAME: Final[str] = 'strict_pyproject.toml'

DEFAULT_CONFIG_DIR: Final[Path] = ROOT_TESTS_MYPY_DIR / DEFAULT_CONFIG_NAME
STRICT_CONFIG_DIR: Final[Path] = ROOT_TESTS_MYPY_DIR / STRICT_CONFIG_NAME
INPUT_PATH: Final[Path] = ROOT_TESTS_MYPY_DIR / 'cases'

DEFAULT_MODULE_NAME: Final[str] = 'module'
DEFAULT_MYPY_OUT_FILENAME: Final[str] = 'default_mypy_out.txt'
STRICT_MYPY_OUT_FILENAME: Final[str] = 'strict_mypy_out.txt'
def _get_mypy_expected_out_by_path(path: Path) -> str:
    return path.read_text()


check_default_dirs = [  # FIXME: os.walk
    'path',
    'header',
    'cookie',
    'query',
    'body',
    'check_type',
]


@pytest.mark.parametrize('default_dir', check_default_dirs)
@pytest.mark.parametrize(
    'config_dir, config_name, out_file',
    [
        pytest.param(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_NAME, DEFAULT_MYPY_OUT_FILENAME, id='default'),
        pytest.param(STRICT_CONFIG_DIR, STRICT_CONFIG_NAME, STRICT_MYPY_OUT_FILENAME, id='strict'),
    ],
)
def test_default(
    default_dir: str,
    config_dir: Path,
    config_name: str,
    out_file: str,
    tmp_path: Path,
) -> None:
    default_test_module = 'default'

    input_path = INPUT_PATH / default_test_module / default_dir / 'module.py'
    mypy_expected_out_path = INPUT_PATH / default_test_module / default_dir / out_file

    mypy_expected_out = _get_mypy_expected_out_by_path(mypy_expected_out_path)

    cache_dir = tmp_path / Path(config_name).stem

    command = [
        str(input_path),
        '--config-file',
        str(config_dir),
        '--cache-dir',
        str(cache_dir),
        '--show-error-codes',
        '--show-traceback',
    ]

    mypy_out, mypy_err, _mypy_returncode = mypy_api.run(command)
    assert mypy_err == ''

    normalized_mypy_out = (
        mypy_out.replace('packages/rapidy/', '')
        .replace('tests/', '')
        .replace('ported/', '')
        .replace('test_mypy/', '')
        .replace('rapidy_core.parameters.http', 'rapidy.parameters.http')
        .replace('for parameter ', 'for argument ')
        .replace('parameter has type', 'argument has type')
    )
    assert normalized_mypy_out == mypy_expected_out
