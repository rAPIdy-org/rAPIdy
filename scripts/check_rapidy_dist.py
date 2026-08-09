from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path

REQUIRED_WHEEL = {
    "rapidy/__init__.py",
    "rapidy/http.py",
    "rapidy/depends.py",
    "rapidy/background.py",
    "rapidy/observability.py",
    "rapidy/problems.py",
    "rapidy/responses/files.py",
    "rapidy/routing/reverse.py",
    "rapidy/staticfiles.py",
    "rapidy/testing/__init__.py",
    "rapidy/py.typed",
}
FORBIDDEN_PARTS = (
    "/benchmarks/",
    "/docs/",
    "/examples/",
    "/roadmap/",
    "/spikes/",
    "/tests/",
    "rapidy/mypy/",
)


def check_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_WHEEL - names
        assert not missing, f"missing wheel members: {sorted(missing)}"
        assert not any(
            part in f"/{name}" for name in names for part in FORBIDDEN_PARTS
        ), "forbidden wheel member"
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode()
    for expected in (
        "Name: rAPIdy",
        "Version: 2.0.0",
        "License-File: LICENSE",
        "Requires-Python: >=3.12",
        "Requires-Dist: pydantic (>=2.9,<3)",
        "Requires-Dist: rapidy-core (>=0.1,<0.2)",
    ):
        assert expected in metadata, f"missing metadata: {expected}"
    assert "Requires-Dist: aiohttp" not in metadata
    assert "Requires-Dist: dishka" not in metadata
    assert 'Provides-Extra: test' in metadata
    assert 'Provides-Extra: otel' in metadata
    assert 'Requires-Dist: httpx' in metadata and 'extra == "test"' in metadata
    assert 'Requires-Dist: brotli' in metadata and 'extra == "brotli"' in metadata
    assert 'Requires-Dist: opentelemetry-api' in metadata and 'extra == "otel"' in metadata
    assert 'Requires-Dist: opentelemetry-instrumentation-asgi' in metadata and 'extra == "otel"' in metadata


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
    required_suffixes = (
        "/LICENSE",
        "/README.md",
        "/pyproject.toml",
        "/rapidy/__init__.py",
        "/rapidy/py.typed",
    )
    for suffix in required_suffixes:
        assert any(name.endswith(suffix) for name in names), (
            f"missing sdist member: {suffix}"
        )
    assert not any("/benchmarks/" in name for name in names)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sdist", type=Path)
    args = parser.parse_args()
    check_wheel(args.wheel)
    check_sdist(args.sdist)
    print("rapidy distribution contents and metadata: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
