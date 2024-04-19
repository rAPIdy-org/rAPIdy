import os
import platform
from pathlib import Path
from typing import Final

import pytest
from mypy import api as mypy_api

from rapidy.mypy._version import MYPY_VERSION_TUPLE

PY_VERSION_TUPLE = tuple(int(num) for num in platform.python_version_tuple())

ROOT_TESTS_MYPY_DIR: Final[Path] = Path(__file__).parent

DEFAULT_CONFIG_NAME: Final[str] = 'default_pyproject.toml'
STRICT_CONFIG_NAME: Final[str] = 'strict_pyproject.toml'

DEFAULT_CONFIG_DIR: Final[Path] = ROOT_TESTS_MYPY_DIR / DEFAULT_CONFIG_NAME
STRICT_CONFIG_DIR: Final[Path] = ROOT_TESTS_MYPY_DIR / STRICT_CONFIG_NAME
INPUT_PATH: Final[Path] = ROOT_TESTS_MYPY_DIR / 'cases'

DEFAULT_MODULE_NAME: Final[str] = 'module'
DEFAULT_MYPY_OUT_FILENAME: Final[str] = 'default_mypy_out.txt'
STRICT_MYPY_OUT_FILENAME: Final[str] = 'strict_mypy_out.txt'
OLD_STYLE_DEFAULT_MYPY_OUT_FILENAME: Final[str] = 'old_style_default_mypy_out.txt'
OLD_STYLE_STRICT_MYPY_OUT_FILENAME: Final[str] = 'old_style_strict_mypy_out.txt'

raw_param_default_mypy_out_filename: str = DEFAULT_MYPY_OUT_FILENAME
raw_param_strict_mypy_out_filename: str = STRICT_MYPY_OUT_FILENAME

if MYPY_VERSION_TUPLE < (1, 4, 0) or PY_VERSION_TUPLE < (3, 9, 0):
    raw_param_default_mypy_out_filename = OLD_STYLE_DEFAULT_MYPY_OUT_FILENAME
    raw_param_strict_mypy_out_filename = OLD_STYLE_STRICT_MYPY_OUT_FILENAME


def _get_mypy_expected_out_by_path(path: Path) -> str:
    with open(path, 'r') as mypy_out_file:
        return mypy_out_file.read()


check_default_dirs = [
    'path',
    'header',
    'cookie',
    'query',
    'body_stream',
    'body_bytes',
    'body_text',
    'body_json',
    'body_form_data',
    'body_multipart',
    'check_type',
]


@pytest.mark.parametrize('default_dir', check_default_dirs)
@pytest.mark.parametrize(
    'config_dir, config_name, out_file', [
        (DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_NAME, DEFAULT_MYPY_OUT_FILENAME),
        (STRICT_CONFIG_DIR, STRICT_CONFIG_NAME, STRICT_MYPY_OUT_FILENAME),
    ],
)
def test_default(
        default_dir: str,
        config_dir: Path,
        config_name: Path,
        out_file: str,
) -> None:
    default_test_module = 'default'

    input_path = INPUT_PATH / default_test_module / default_dir / 'module.py'
    mypy_expected_out_path = INPUT_PATH / default_test_module / default_dir / out_file

    mypy_expected_out = _get_mypy_expected_out_by_path(mypy_expected_out_path)

    cache_dir = f'.mypy_cache/test-default-{os.path.splitext(config_name)[0]}'

    command = [
        str(input_path),
        '--config-file',
        str(config_dir),
        '--cache-dir',
        cache_dir,
        '--show-error-codes',
        '--show-traceback',
    ]

    mypy_out, mypy_err, mypy_returncode = mypy_api.run(command)
    assert mypy_err == ''

    assert mypy_out == mypy_expected_out


@pytest.mark.parametrize(
    'config_dir, config_name, out_file', [
        (DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_NAME, raw_param_default_mypy_out_filename),
        (STRICT_CONFIG_DIR, STRICT_CONFIG_NAME, raw_param_strict_mypy_out_filename),
    ],
)
def test_raw_param_annotate(
        config_dir: Path,
        config_name: Path,
        out_file: str,
) -> None:
    default_test_module = 'raw_params_annotate'

    input_path = INPUT_PATH / default_test_module / 'module.py'
    mypy_expected_out_path = INPUT_PATH / default_test_module / out_file

    mypy_expected_out = _get_mypy_expected_out_by_path(mypy_expected_out_path)

    cache_dir = f'.mypy_cache/test-raw-param-annotate-{os.path.splitext(config_name)[0]}'

    command = [
        str(input_path),
        '--config-file',
        str(config_dir),
        '--cache-dir',
        cache_dir,
        '--show-error-codes',
        '--show-traceback',
    ]

    mypy_out, mypy_err, mypy_returncode = mypy_api.run(command)
    assert mypy_err == ''

    assert mypy_out == mypy_expected_out
