#!/usr/bin/env python3
"""Controle les anciennes phrases visibles anglaises dans les surfaces publiques."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


PUBLIC_FILES = (
    "README.md",
    "site/index.html",
    "site/js/localization.js",
    "site/manifest.webmanifest",
    "templates/config.yml",
)
PUBLIC_DIRS = (
    ".github",
    "doc",
    "docs",
)
TEXT_SUFFIXES = {".html", ".json", ".md", ".txt", ".yml", ".yaml"}
BANNED_VISIBLE_PHRASES = (
    "High-performance",
    "Quick Start",
    "Features",
    "Screenshots",
    "Live telemetry",
    "Daily Data",
    "Filter a period",
    "Grid & Home",
    "CSV Download",
    "Download .csv reports",
    "The download failed",
    "Production overview",
    "runtime reference",
    "By Day",
    "By Month",
    "By Year",
    "All Time",
)


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    phrase: str


def iter_public_text_files(root: Path):
    for file_name in PUBLIC_FILES:
        path = root / file_name
        if path.exists():
            yield path
    for directory_name in PUBLIC_DIRS:
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def scan(root: Path) -> list[Finding]:
    root = root.resolve()
    patterns = [
        (phrase, re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE))
        for phrase in BANNED_VISIBLE_PHRASES
    ]
    findings: list[Finding] = []
    for path in sorted(set(iter_public_text_files(root))):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for phrase, pattern in patterns:
                if pattern.search(line):
                    findings.append(Finding(rel, line_number, phrase))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scanne les surfaces publiques pour les anciennes phrases anglaises."
    )
    parser.add_argument("--root", default=".", help="Racine du depot")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    findings = scan(Path(args.root))
    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(f"{finding.file}:{finding.line}: phrase anglaise: {finding.phrase}")
        if not findings:
            print("Aucune ancienne phrase anglaise visible detectee.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
