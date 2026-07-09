from pathlib import Path

from scripts import privacy_scan


def test_privacy_scan_detects_precise_environment_leaks(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "site").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        "Acces: phocos.local\nIP: 192.168.1.31\nPath: /Users/adrien/project\n",
        encoding="utf-8",
    )
    (tmp_path / "site" / "ok.html").write_text("PiPhocos local", encoding="utf-8")

    findings = privacy_scan.scan(tmp_path)

    assert {finding.rule for finding in findings} == {
        "hostname_precis",
        "ip_privee_precise",
        "chemin_local_precis",
        "identite_personnelle",
    }


def test_privacy_scan_ignores_vendored_site_lib(tmp_path):
    (tmp_path / "site" / "lib").mkdir(parents=True)
    (tmp_path / "site" / "lib" / "vendor.js").write_text(
        "const sample = 'phocos.local';",
        encoding="utf-8",
    )

    assert privacy_scan.scan(tmp_path) == []


def test_privacy_scan_detects_public_image_metadata(tmp_path):
    (tmp_path / "doc").mkdir()
    (tmp_path / "doc" / "screen.webp").write_bytes(
        b"RIFF....WEBP XMP Pixelmator Screenshot /Users/adrien/Desktop"
    )

    findings = privacy_scan.scan(tmp_path)

    assert {finding.rule for finding in findings} >= {
        "metadata_xmp_exif",
        "metadata_createur",
        "metadata_appareil",
        "chemin_local_precis",
    }
