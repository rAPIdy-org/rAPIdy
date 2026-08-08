from pathlib import Path

from mypy import api as mypy_api


def run_mypy(tmp_path: Path, source: str) -> tuple[str, str, int]:
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\nplugins = rapidy_core.mypy\n", encoding="utf-8")
    module = tmp_path / "example.py"
    module.write_text(source, encoding="utf-8")
    return mypy_api.run(
        [
            "--config-file",
            str(config),
            "--no-incremental",
            "--show-error-codes",
            str(module),
        ],
    )


def test_plugin_activates(tmp_path: Path) -> None:
    stdout, stderr, status = run_mypy(
        tmp_path,
        "from rapidy_core.parameters.http import QueryParam\nq = QueryParam()\n",
    )

    assert status == 0, stdout + stderr


def test_marker_typed_by_plugin(tmp_path: Path) -> None:
    stdout, stderr, status = run_mypy(
        tmp_path,
        "from rapidy_core.parameters.http import QueryParam\nq: int = QueryParam(1)\n",
    )

    assert status == 0, stdout + stderr


def test_negative_default_on_path_param_caught(tmp_path: Path) -> None:
    stdout, stderr, status = run_mypy(
        tmp_path,
        "from rapidy_core.parameters.http import PathParam\nx = PathParam('oops')\n",
    )

    assert status == 1, stdout + stderr
    assert "rapidy-param" in stdout
    assert '"default" or "default_factory" cannot be specified' in stdout


def test_negative_default_and_factory_together(tmp_path: Path) -> None:
    stdout, stderr, status = run_mypy(
        tmp_path,
        "from rapidy_core.parameters.http import QueryParam\n"
        "y = QueryParam('d', default_factory=lambda: 'f')\n",
    )

    assert status == 1, stdout + stderr
    assert "rapidy-param" in stdout
    assert "cannot be specified together" in stdout
