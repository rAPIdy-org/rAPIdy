from __future__ import annotations

import argparse
import email
import re
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DistributionContract:
    metadata_name: str
    module: str
    requires_python: str
    required_dependencies: tuple[str, ...]
    forbidden_dependencies: tuple[str, ...]


CONTRACTS = {
    "rapidy": DistributionContract(
        metadata_name="rAPIdy",
        module="rapidy",
        requires_python=">=3.12",
        required_dependencies=("multidict", "pydantic", "python-multipart", "rapidy-core"),
        forbidden_dependencies=("aiohttp", "dishka", "rapidy-client"),
    ),
    "rapidy-client": DistributionContract(
        metadata_name="rapidy-client",
        module="rapidy_client",
        requires_python=">=3.12",
        required_dependencies=("httpx2", "pydantic", "pydantic-settings", "rapidy-core", "wsproto", "yarl"),
        forbidden_dependencies=("dishka", "rapidy"),
    ),
    "rapidy-core": DistributionContract(
        metadata_name="rapidy-core",
        module="rapidy_core",
        requires_python=">=3.12",
        required_dependencies=("dishka", "pydantic"),
        forbidden_dependencies=("rapidy", "rapidy-client"),
    ),
}

FORBIDDEN_PATH_PARTS = (
    "/.agents/",
    "/.codex/",
    "/audits/",
    "/benchmarks/",
    "/docs/",
    "/examples/",
    "/prompts/",
    "/roadmap/",
    "/spikes/",
    "/tests/",
)


def _normalized(value: str) -> str:
    return value.casefold().replace("_", "-")


def _metadata_from_wheel(path: Path) -> tuple[email.message.Message, set[str]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = email.message_from_bytes(archive.read(metadata_name))
    return metadata, names


def _check_metadata(metadata: email.message.Message, contract: DistributionContract) -> None:
    assert metadata["Name"] == contract.metadata_name
    assert metadata["Version"]
    assert metadata["Requires-Python"] == contract.requires_python
    assert "daniil.grois@gmail.com" in (metadata["Author-email"] or "")
    license_value = metadata["License-Expression"] or metadata["License"] or ""
    assert license_value.strip() == "MIT"

    dependencies = tuple(metadata.get_all("Requires-Dist", ()))
    base_dependencies = tuple(value for value in dependencies if "extra ==" not in value)
    normalized = tuple(
        _normalized(re.split(r"[\s(<>=!~;\[]", value, maxsplit=1)[0])
        for value in base_dependencies
    )
    for dependency in contract.required_dependencies:
        assert dependency in normalized, f"missing base dependency: {dependency}"
    for dependency in contract.forbidden_dependencies:
        assert dependency not in normalized, f"forbidden base dependency: {dependency}"


def check_wheel(path: Path, contract: DistributionContract) -> str:
    metadata, names = _metadata_from_wheel(path)
    _check_metadata(metadata, contract)
    assert f"{contract.module}/__init__.py" in names
    assert f"{contract.module}/py.typed" in names
    assert not any(
        part in f"/{name.casefold()}" for name in names for part in FORBIDDEN_PATH_PARTS
    ), "forbidden wheel member"
    assert not any(name.endswith((".pyc", ".pyo")) or "__pycache__" in name for name in names)

    if contract.module == "rapidy_client":
        with zipfile.ZipFile(path) as archive:
            entry_points_name = next(
                (name for name in names if name.endswith(".dist-info/entry_points.txt")),
                None,
            )
            entry_points = "" if entry_points_name is None else archive.read(entry_points_name).decode()
        assert "pytest11" not in entry_points
        assert "rapidy_client.testing.plugin" not in entry_points
    return metadata["Version"]


def check_sdist(path: Path, contract: DistributionContract, version: str) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        package_info_name = next(name for name in names if name.endswith("/PKG-INFO"))
        package_info_file = archive.extractfile(package_info_name)
        assert package_info_file is not None
        metadata = email.message_from_bytes(package_info_file.read())
    _check_metadata(metadata, contract)
    assert metadata["Version"] == version
    for suffix in ("/LICENSE", "/README.md", "/pyproject.toml", f"/{contract.module}/__init__.py"):
        assert any(name.endswith(suffix) for name in names), f"missing sdist member: {suffix}"
    assert not any(
        part in f"/{name.casefold()}" for name in names for part in FORBIDDEN_PATH_PARTS
    ), "forbidden sdist member"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution", choices=sorted(CONTRACTS))
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sdist", type=Path)
    args = parser.parse_args()

    contract = CONTRACTS[args.distribution]
    version = check_wheel(args.wheel, contract)
    check_sdist(args.sdist, contract, version)
    print(f"{args.distribution} release artifacts: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
