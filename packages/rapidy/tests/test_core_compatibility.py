from __future__ import annotations

import pytest
import rapidy_core

from rapidy._core_compat import ensure_core_compatibility, REQUIRED_CORE_API_VERSION


def test_server_accepts_current_core_api_epoch() -> None:
    assert rapidy_core.CORE_API_VERSION == REQUIRED_CORE_API_VERSION
    ensure_core_compatibility()


def test_server_rejects_incompatible_core_api_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rapidy_core, 'CORE_API_VERSION', REQUIRED_CORE_API_VERSION + 1)

    with pytest.raises(ImportError, match=r'rAPIdy 2\.0 requires rapidy-core API epoch 1'):
        ensure_core_compatibility()
