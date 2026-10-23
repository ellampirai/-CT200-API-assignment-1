
from pathlib import Path

from app.versioning import compare_versions


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

OLD_PDF = DATA_DIR / "ct200_manual.pdf"
NEW_PDF = DATA_DIR / "ct200_manual_v2.pdf"


def test_version_comparison_detects_expected_changes():
    changes = compare_versions(OLD_PDF, NEW_PDF)

    changed_sections = {
        item["section_number"]
        for item in changes
        if item["status"] == "changed"
    }

    added_sections = {
        item["section_number"]
        for item in changes
        if item["status"] == "added"
    }

    removed_sections = {
        item["section_number"]
        for item in changes
        if item["status"] == "removed"
    }

    assert changed_sections == {"2.1.1.1", "3.2", "4.2", "4.3"}
    assert added_sections == {"5.3"}
    assert removed_sections == set()


def test_version_comparison_returns_content_hashes():
    changes = compare_versions(OLD_PDF, NEW_PDF)

    for item in changes:
        if item["status"] == "changed":
            assert item["old_hash"] is not None
            assert item["new_hash"] is not None

        elif item["status"] == "added":
            assert item["old_hash"] is None
            assert item["new_hash"] is not None

        elif item["status"] == "removed":
            assert item["old_hash"] is not None
            assert item["new_hash"] is None
