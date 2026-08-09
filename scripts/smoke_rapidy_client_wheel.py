from __future__ import annotations

import importlib
import pkgutil
from importlib import metadata

import rapidy_client
from rapidy_client import HttpClient, UpstreamConfig

OPTIONAL_MODULES = frozenset({"rapidy_client.testing.plugin"})


def main() -> int:
    assert metadata.version("rapidy-client")
    config = UpstreamConfig(base_url="https://wheel.example")
    client = HttpClient(config)
    request = client._build_request("GET", "/health")
    assert request.url._raw_str() == "https://wheel.example/health"
    modules = sorted(
        module.name
        for module in pkgutil.walk_packages(
            rapidy_client.__path__,
            prefix="rapidy_client.",
        )
    )
    for module in modules:
        if module in OPTIONAL_MODULES:
            continue
        importlib.import_module(module)
    assert modules
    print("rapidy-client wheel imports and request builder: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
