#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_no_secrets.py
@brief No file tracked by the version control holds an API key, and the key files are ignored.

@details Scans the content of `git ls-files` for Google keys (`AIza` + 35 characters, the newer `AQ.` form) and
for assignments such as `api_key = "..."` with a long literal. A hit prints only file, line number and the kind
of pattern, never the matched text.
"""

import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = {
    "google key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "google key (AQ form)": re.compile(r"\bAQ\.[A-Za-z0-9_-]{30,}"),
    "api key assignment": re.compile(r"""api[_-]?key\s*[=:]\s*['"][A-Za-z0-9_-]{20,}""", re.I),
}
MAX_BYTES = 2_000_000


def tracked_files():
    """!
    @brief Paths of the files tracked by git.
    @return list[pathlib.Path] Absolute paths, or an empty list when git is not available.
    """
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    return [ROOT / p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def test_no_key_like_text_in_tracked_files():
    files = tracked_files()
    if not files:
        pytest.skip("git is not available")
    hits = []
    for p in files:
        try:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                continue
            text = p.read_bytes().decode("utf-8", "ignore")
        except OSError:
            continue
        for kind, rx in PATTERNS.items():
            for m in rx.finditer(text):
                hits.append(f"{p.relative_to(ROOT)}:{text.count(chr(10), 0, m.start()) + 1} ({kind})")
    assert not hits, "key-like text in tracked files (not shown): " + ", ".join(hits)


def test_the_scanner_catches_a_key_shaped_string():
    fake = "AIza" + "x" * 35
    assert PATTERNS["google key"].search(f"k={fake}")
    assert PATTERNS["api key assignment"].search('api_key = "' + "y" * 24 + '"')
    assert PATTERNS["google key (AQ form)"].search("AQ." + "z" * 40)


def test_key_files_and_papers_are_ignored():
    lines = (ROOT / ".gitignore").read_text().split("\n")
    for entry in (".ocr_keys", "papers/", "*.key"):
        assert entry in lines, f"{entry} must be in .gitignore"
