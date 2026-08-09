from __future__ import annotations

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
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


def test_publish_job_can_only_use_artifacts_from_verify_job() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )
    verify_block, publish_block = workflow.split("\n  publish:\n", maxsplit=1)

    assert "pytest packages/rapidy_core/tests" in verify_block
    assert "pytest packages/rapidy_client/tests" in verify_block
    assert "pytest packages/rapidy/tests" in verify_block
    assert "scripts/check_release_dist.py" in verify_block
    assert "uv pip install dist/support/*.whl dist/release/*.whl" in verify_block
    assert "actions/upload-artifact@v4" in verify_block
    assert "needs: verify" in publish_block
    assert "actions/download-artifact@v4" in publish_block
    assert "uv publish dist/release/*" in publish_block
    assert "uv build" not in publish_block


def test_release_artifact_gate_covers_all_distributions() -> None:
    gate = (REPOSITORY_ROOT / "scripts" / "check_release_dist.py").read_text(
        encoding="utf-8"
    )
    assert '"rapidy"' in gate
    assert '"rapidy-client"' in gate
    assert '"rapidy-core"' in gate
    assert "daniil.grois@gmail.com" in gate
    assert "FORBIDDEN_PATH_PARTS" in gate
