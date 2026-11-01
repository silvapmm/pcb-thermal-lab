#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_no_secrets.py
@brief No file tracked by the version control holds an API key, and the key files are ignored.

@details Scans the content of `git ls-files` for Google keys (`AIza` + 35 characters, the newer `AQ.` form, which
may hold further dots) and for assignments such as `api_key = "..."` with a long literal. On request
(`PCBT_SCAN_KEY_VALUES=1`, by the maintainer; skipped otherwise so that routine runs never read the key) and when
the local key file `.ocr_keys` exists and is safe, the tracked files are also searched for the exact key values, so
that a key of an unexpected shape is caught too; the values stay inside a helper and never reach an assertion message. A hit prints
only file, line number and the kind of pattern, never the matched text.
"""

import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = {
    "google key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "google key (AQ form)": re.compile(r"\bAQ\.[A-Za-z0-9_.-]{30,}"),
    "api key assignment": re.compile(r"""api[_-]?key\s*[=:]\s*['"][A-Za-z0-9_.-]{20,}""", re.I),
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


def files_holding_local_keys(files):
    """!
    @brief Names of the tracked files that contain one of the keys of the local `.ocr_keys` file.
    @details The key values live only in this function's frame: the caller gets file names, so that neither an
             assertion message nor `pytest -l` (locals in tracebacks) can show a key.
    @param files Tracked files.
    @return list[str]|None Relative paths with a hit; None when there is no key file (or it is unsafe).
    """
    import sys
    sys.path.insert(0, str(ROOT))
    from tools.ocr import keys
    values = None
    for root in keys.project_roots():
        path = root / keys.KEY_FILE_NAME
        if path.is_file():
            try:
                values = [v.encode() for v in keys.parse_key_file(path).values() if len(v) >= 16]
            except keys.KeyError_:
                return None
            break
    if not values:
        return None
    hits = []
    for p in files:
        try:
            if p.is_file() and p.stat().st_size <= MAX_BYTES and any(v in p.read_bytes() for v in values):
                hits.append(str(p.relative_to(ROOT)))
        except OSError:
            continue
    del values
    return hits


def test_no_local_key_value_in_tracked_files():
    # Opt-in (PCBT_SCAN_KEY_VALUES=1, run by the maintainer before a push): the routine battery, run by agents,
    # must not read the real key file at all.
    import os
    if os.environ.get("PCBT_SCAN_KEY_VALUES") != "1":
        pytest.skip("set PCBT_SCAN_KEY_VALUES=1 to search the tracked files for the values of .ocr_keys")
    files = tracked_files()
    if not files:
        pytest.skip("git is not available")
    hits = files_holding_local_keys(files)
    if hits is None:
        pytest.skip("no safe local .ocr_keys file")
    assert not hits, "a key of .ocr_keys is in tracked files (not shown): " + ", ".join(hits)


def test_the_scanner_catches_a_key_shaped_string():
    fake = "AIza" + "x" * 35
    assert PATTERNS["google key"].search(f"k={fake}")
    assert PATTERNS["api key assignment"].search('api_key = "' + "y" * 24 + '"')
    assert PATTERNS["google key (AQ form)"].search("AQ." + "z" * 40)
    # The AQ form with further dots (53 characters in all, as the keys of AI Studio are), even with a short first segment.
    assert PATTERNS["google key (AQ form)"].search("AQ." + "a" * 12 + "." + "b" * 37)


def test_key_files_and_papers_are_ignored():
    lines = (ROOT / ".gitignore").read_text().split("\n")
    for entry in (".ocr_keys", "papers/", "*.key"):
        assert entry in lines, f"{entry} must be in .gitignore"
