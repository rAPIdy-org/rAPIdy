from __future__ import annotations

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
HOWTO_MIN = 15


def test_adr_has_no_internal_migration_section() -> None:
    adr = PACKAGE_ROOT / "docs" / "adr" / "http-client-redesign.md"

    assert adr.is_file()
    assert (
        re.search(r"^##\s+7\.", adr.read_text(encoding="utf-8"), re.MULTILINE) is None
    )


def test_readme_and_changelog_are_present() -> None:
    assert (PACKAGE_ROOT / "README.md").is_file()
    assert (PACKAGE_ROOT / "CHANGELOG.md").is_file()


def test_required_howto_set_is_complete() -> None:
    howto = PACKAGE_ROOT / "docs" / "how-to"
    pages = sorted(howto.glob("*.md"))

    assert len(pages) >= HOWTO_MIN
    assert (howto / "di.md") in pages


def test_di_howto_documents_active_composition_model() -> None:
    content = (PACKAGE_ROOT / "docs" / "how-to" / "di.md").read_text(encoding="utf-8")

    assert "HttpApp" in content
    assert content.count("Component(") >= 2
    assert "binds to" in content
    assert "no separate `[di]` extra" in content


def test_golden_and_property_suites_use_no_real_sleep() -> None:
    violations: list[str] = []
    for directory in ("golden", "property"):
        for source in sorted((PACKAGE_ROOT / "tests" / directory).glob("*.py")):
            content = source.read_text(encoding="utf-8")
            if "time.sleep(" in content or "asyncio.sleep(" in content:
                violations.append(str(source.relative_to(PACKAGE_ROOT)))

    assert violations == []
