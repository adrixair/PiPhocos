from pathlib import Path

import pytest

from scripts import privacy_scan


LOCAL_HOST = ".".join(("phocos", "local"))
PRIVATE_IP = ".".join(("192", "168", "50", "10"))
LOCAL_PATH = Path("/Users") / "example" / "project"


def test_privacy_scan_detects_precise_environment_leaks(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "site").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        f"Acces: {LOCAL_HOST}\nIP: {PRIVATE_IP}\nPath: {LOCAL_PATH}\n",
        encoding="utf-8",
    )
    (tmp_path / "site" / "ok.html").write_text("PiPhocos local", encoding="utf-8")

    findings = privacy_scan.scan(tmp_path)

    assert {finding.rule for finding in findings} == {
        "hostname_precis",
        "ip_privee_precise",
        "chemin_local_precis",
    }


@pytest.mark.parametrize("filename", ["pytest/test_example.py", "dockerfile", "supervisord.conf", "site/app.webmanifest"])
def test_privacy_scan_covers_public_tests_and_configuration(tmp_path, filename):
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"path = {str(LOCAL_PATH)!r}", encoding="utf-8")

    assert [(finding.file, finding.rule) for finding in privacy_scan.scan(tmp_path)] == [
        (filename, "chemin_local_precis"),
    ]


def test_privacy_scan_ignores_vendored_site_lib(tmp_path):
    (tmp_path / "site" / "lib").mkdir(parents=True)
    (tmp_path / "site" / "lib" / "vendor.js").write_text(
        f"const sample = '{LOCAL_HOST}';",
        encoding="utf-8",
    )

    assert privacy_scan.scan(tmp_path) == []


def test_privacy_scan_detects_public_image_metadata(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "screen.webp").write_bytes(
        f"RIFF....WEBP XMP Pixelmator Screenshot {LOCAL_PATH}".encode("ascii")
    )

    findings = privacy_scan.scan(tmp_path)

    assert {finding.rule for finding in findings} >= {
        "metadata_xmp_exif",
        "metadata_createur",
        "metadata_appareil",
        "chemin_local_precis",
    }
