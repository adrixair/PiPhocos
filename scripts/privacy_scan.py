#!/usr/bin/env python3
"""Controle les surfaces publiques pour eviter les fuites d'environnement."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INCLUDE_DIRS = (
    ".github",
    "backend",
    "doc",
    "docs",
    "scripts",
    "site",
    "templates",
)
DEFAULT_INCLUDE_FILES = ("README.md", "docker-compose.yml", "dockerfile", "supervisord.conf")
DEFAULT_SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "site/lib",
}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".yml",
    ".yaml",
}
IMAGE_SUFFIXES = {
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".webp",
}


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    match: str


RULES = (
    (
        "hostname_precis",
        re.compile(r"\b(?:phocos\.local|phocos\.home)\b", re.IGNORECASE),
    ),
    (
        "identite_personnelle",
        re.compile(
            r"\b(?:adri" + r"xair|adri" + r"en|le" + r"jeune)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chemin_local_precis",
        re.compile(r"(?:/Users/[A-Za-z0-9._-]+|/home/(?!<)[A-Za-z0-9._-]+)"),
    ),
    (
        "ip_privee_precise",
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
    (
        "secret_probable",
        re.compile(
            r"\b(?:ptr_[A-Za-z0-9+/=_-]{12,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})\b"
        ),
    ),
    (
        "email_probable",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
)
BINARY_RULES = (
    ("metadata_xmp_exif", re.compile(rb"\b(?:xmp|exif|photoshop)\b", re.IGNORECASE)),
    ("metadata_createur", re.compile(rb"\b(?:creator|author|pixelmator)\b", re.IGNORECASE)),
    ("metadata_appareil", re.compile(rb"\b(?:Mac\d+,\d+|iCloud|Screenshot)\b", re.IGNORECASE)),
    (
        "identite_personnelle",
        re.compile(
            rb"\b(?:adri" + rb"xair|adri" + rb"en|le" + rb"jeune)\b",
            re.IGNORECASE,
        ),
    ),
    ("chemin_local_precis", re.compile(rb"(?:/Users/[A-Za-z0-9._-]+|/home/(?!<)[A-Za-z0-9._-]+)")),
    (
        "ip_privee_precise",
        re.compile(
            rb"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            rb"192\.168\.\d{1,3}\.\d{1,3}|"
            rb"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
)


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    rel_text = rel.as_posix()
    parts = set(rel.parts)
    if parts & {".git", ".pytest_cache", "__pycache__"}:
        return True
    return any(rel_text == skip or rel_text.startswith(skip + "/") for skip in DEFAULT_SKIP_DIRS)


def iter_public_text_files(root: Path):
    roots = [root / name for name in DEFAULT_INCLUDE_DIRS]
    explicit = [root / name for name in DEFAULT_INCLUDE_FILES]
    for candidate in explicit:
        if candidate.exists() and candidate.is_file() and candidate.suffix in TEXT_SUFFIXES:
            yield candidate

    for directory in roots:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if _should_skip(path, root) or not path.is_file():
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def iter_public_binary_files(root: Path):
    roots = [root / name for name in DEFAULT_INCLUDE_DIRS]
    for directory in roots:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if _should_skip(path, root) or not path.is_file():
                continue
            if path.suffix.lower() in IMAGE_SUFFIXES:
                yield path


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings

    rel = path.relative_to(root).as_posix()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in RULES:
            for match in pattern.finditer(line):
                findings.append(
                    Finding(
                        file=rel,
                        line=line_number,
                        rule=rule,
                        match=match.group(0),
                    )
                )
    return findings


def scan_binary_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    data = path.read_bytes()
    rel = path.relative_to(root).as_posix()
    for rule, pattern in BINARY_RULES:
        for match in pattern.finditer(data):
            findings.append(
                Finding(
                    file=rel,
                    line=0,
                    rule=rule,
                    match=match.group(0).decode("latin-1", "replace"),
                )
            )
    return findings


def scan(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    for path in sorted(set(iter_public_text_files(root))):
        findings.extend(scan_file(path, root))
    for path in sorted(set(iter_public_binary_files(root))):
        findings.extend(scan_binary_file(path, root))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scanne les fichiers publics pour eviter les fuites d'environnement."
    )
    parser.add_argument("--root", default=".", help="Racine du depot")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    findings = scan(Path(args.root))
    rows = [finding.__dict__ for finding in findings]
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(
                f"{finding.file}:{finding.line}: {finding.rule}: {finding.match}"
            )
        if not findings:
            print("Aucune fuite d'environnement detectee.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
