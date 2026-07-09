from scripts import public_language_scan


def test_public_language_scan_detects_old_visible_english(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        "# Quick Start\nDaily Data\n",
        encoding="utf-8",
    )

    findings = public_language_scan.scan(tmp_path)

    assert [finding.phrase for finding in findings] == ["Quick Start", "Daily Data"]


def test_public_language_scan_accepts_french_surface(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ok.md").write_text(
        "# Installation rapide\nDonnees journalieres\n",
        encoding="utf-8",
    )

    assert public_language_scan.scan(tmp_path) == []
