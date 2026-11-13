#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_third_party_text.py
@brief Guard against third-party text entering the public history by accident.

The papers library (`papers/`, OCR conversions, summaries of copyrighted works) is local and never
committed (reviewer's opinion `releases/2.7.0/final-opinion/papers-in-git-opinion.md`). The tests run over the
tracked files (`git ls-files`) and fail on: a path under `papers/`, OCR page markers in a Markdown file,
the SHA-256 or the title of a confidential file, and a bibliography entry without a licence field.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The ODB++ specification named in CLAUDE.md ('Papers library and OCR'); its title is built in pieces so
# that this file does not contain the strings it forbids.
CONFIDENTIAL_TITLES = ("ODB" + "++ Format Specification", "Odbpp" + "Spec81U4")
OCR_MARKER = re.compile(r"<!--\s*page\s+\d+|reading_status:\s*machine")
# Files that only describe the markers.
MARKER_EXCEPTIONS = {"tools/ocr/README.md", "tests/test_third_party_text.py",
                     "releases/2.7.0/final-opinion/papers-in-git-opinion.md"}
LICENCE_VALUES = re.compile(
    r"^(public domain|all rights reserved|confidential|not checked|"
    r"[A-Za-z0-9][A-Za-z0-9.+-]*(?: (?:OR|AND|WITH) [A-Za-z0-9.+-]+)*)$")


GUARD_LIST = "tools/ocr/data/confidential.json"


def guard_hashes():
    """!
    @brief SHA-256 values of the confidential files listed by the OCR tool's guard.

    @return list[str] Lower-case hexadecimal digests.
    """
    cfg = json.loads((ROOT / GUARD_LIST).read_text())
    return [h.lower() for h in cfg.get("sha256", [])]


def tracked_files():
    """!
    @brief List the files tracked by git.

    @return list[str] Paths relative to the repository root.
    """
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if (ROOT / p).is_file()]


def test_no_tracked_path_under_papers():
    """!
    @brief The local papers library must never be tracked.

    @return None
    """
    assert [p for p in tracked_files() if p.startswith("papers/")] == []


def test_no_ocr_markers_in_tracked_markdown():
    """!
    @brief No tracked Markdown file carries OCR page markers (a sign of a converted paper).

    @return None
    """
    bad = [p for p in tracked_files() if p.endswith(".md") and p not in MARKER_EXCEPTIONS
           and OCR_MARKER.search((ROOT / p).read_text(errors="ignore"))]
    assert bad == []


def test_no_confidential_title_in_tracked_files():
    """!
    @brief The confidential specification's title or key must not appear in any tracked text file.

    @return None
    """
    bad = []
    for p in tracked_files():
        if p.endswith((".png", ".gif", ".ico", ".icns", ".json")):
            continue
        text = (ROOT / p).read_text(errors="ignore")
        # The hashes of the guard's own list are the only place where they may appear.
        if p != GUARD_LIST and any(h in text.lower() for h in guard_hashes()):
            bad.append(p)
        if any(t in text for t in CONFIDENTIAL_TITLES) and p not in ALLOWED_CONFIDENTIAL_NAME:
            bad.append(p)
    assert bad == []


# Files that must name the guarded file to enforce or describe the guard (name only, never content).
ALLOWED_CONFIDENTIAL_NAME = {"tools/ocr/papermap.py", "CLAUDE.md", "research/theory/BIBLIOGRAPHY.md",
                             "releases/2.7.0/final-opinion/papers-in-git-opinion.md", "tools/ocr/README.md",
                             "tests/test_ocr_tool.py"}


def test_bibliography_entries_have_a_licence():
    """!
    @brief Every entry of the theory bibliography has a licence field with an allowed value.

    @return None
    """
    lines = (ROOT / "research/theory/BIBLIOGRAPHY.md").read_text().splitlines()
    missing, wrong, n = [], [], 0
    for i, line in enumerate(lines):
        if not line.startswith("### ["):
            continue
        n += 1
        m = re.search(r"\*\*Licence:\*\* (.*?)\. \*\*Source URL:\*\*", " ".join(lines[i + 1:i + 4]))
        if not m:
            missing.append(line)
        elif not LICENCE_VALUES.match(m.group(1)):
            wrong.append((line, m.group(1)))
    assert n > 200 and missing == [] and wrong == []
