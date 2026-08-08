from __future__ import annotations

import email
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


@pytest.fixture(scope="module")
def distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[Path, Path]]:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required for the distribution release gate")
    output = tmp_path_factory.mktemp("rapidy-client-dist")
    subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-cache",
            "--package",
            "rapidy-client",
            "--out-dir",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(output.glob("rapidy_client-*.whl"))
    sdist = next(output.glob("rapidy_client-*.tar.gz"))
    yield wheel, sdist


def test_py_typed_is_packaged(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        assert "rapidy_client/py.typed" in archive.namelist()


def test_wheel_public_imports(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    code = """
import sys
sys.path.insert(0, sys.argv[1])
from rapidy_client import Result, bind, get, sse, ws
from rapidy_client.di import HttpApp
from rapidy_client.schema import Body, PathParam, QueryParam
from rapidy_client.wsse import SSEStream, WSSocket
assert all((Result, bind, get, sse, ws, HttpApp, Body, PathParam, QueryParam, SSEStream, WSSocket))
"""
    subprocess.run(
        [sys.executable, "-I", "-c", code, str(wheel)],
        cwd=REPOSITORY_ROOT,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COV_CORE_")
        },
        check=True,
        capture_output=True,
        text=True,
    )


def test_all_source_modules_import_in_fresh_interpreter() -> None:
    code = """
import importlib
import pkgutil
import rapidy_client
modules = sorted(
    module.name
    for module in pkgutil.walk_packages(
        rapidy_client.__path__,
        prefix="rapidy_client.",
    )
)
for module in modules:
    importlib.import_module(module)
assert modules
"""
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_sdist_contains_sources_and_docs(distributions: tuple[Path, Path]) -> None:
    _, sdist = distributions
    with tarfile.open(sdist, mode="r:gz") as archive:
        names = archive.getnames()
        package_info = next(name for name in names if name.endswith("/PKG-INFO"))
        metadata = email.message_from_bytes(archive.extractfile(package_info).read())

    assert any(name.endswith("/pyproject.toml") for name in names)
    assert any(name.endswith("/README.md") for name in names)
    assert metadata["License"] == "MIT"
    assert any(name.endswith("/rapidy_client/__init__.py") for name in names)
    assert not any(
        "roadmap" in name.casefold() or "prototype" in name.casefold() for name in names
    )


def test_distribution_metadata_dependencies(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = email.message_from_bytes(archive.read(metadata_name))

    dependencies = metadata.get_all("Requires-Dist", [])
    assert metadata["Requires-Python"] == ">=3.13"
    assert any(value.startswith("rapidy-core>=0.1,<0.2") for value in dependencies)
    assert any(value.startswith("pydantic>=2.9") for value in dependencies)
    assert any(value.startswith("httpx2>=2.5") for value in dependencies)
    assert any(value.startswith("wsproto>=1.3") for value in dependencies)
    assert not any("dishka" in value.casefold() for value in dependencies)
