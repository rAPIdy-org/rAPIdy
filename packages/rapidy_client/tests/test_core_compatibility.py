from __future__ import annotations

import pytest
import rapidy_core
from rapidy_client._core_compat import REQUIRED_CORE_API_VERSION, ensure_core_compatibility


def test_client_accepts_current_core_api_epoch() -> None:
    assert rapidy_core.CORE_API_VERSION == REQUIRED_CORE_API_VERSION
    ensure_core_compatibility()


def test_client_rejects_incompatible_core_api_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rapidy_core, "CORE_API_VERSION", REQUIRED_CORE_API_VERSION + 1)

    with pytest.raises(ImportError, match=r"rapidy-client 0\.1 requires rapidy-core API epoch 1"):
        ensure_core_compatibility()
