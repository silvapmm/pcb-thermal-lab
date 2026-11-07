#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_license_header.py
@brief Every tracked source, script and configuration file that can hold a comment starts with the copyright and licence notice of the project.
@details Python files: the two comment lines come first (after a shebang or an encoding line) and before the docstring of the module. Shell scripts:
         after the shebang. HTML: an HTML comment right after the doctype line (the doctype must stay first for standards mode). Files with
         `#` comments (`.gitignore`, `requirements*.txt`, `.toml`, `.yml`, `.yaml`, `.cfg`, `.ini`, `Makefile`): the two lines first. Exempt: data files
         that cannot hold a comment (JSON, CSV, images, icons), `LICENSE`, patches, plain-text data (`tools/ocr/data/prompt.txt`),
         Markdown documents (they carry the 'Author and license' statement), the agent instructions in `.claude/`, generated outputs and
         third-party material. The list of files is `git ls-files`, so an untracked scratch file is not checked.
"""

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE1 = "Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved."
LINE2 = "This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution."
HEADER = ("#  " + LINE1, "#  " + LINE2)
HTML_HEADER = ("<!--", "  " + LINE1, "  " + LINE2, "-->")
FOLDERS = ("pcbthermal", "tests", "examples", "research", "releases", "tools")
HASH_NAMES = {".gitignore", "Makefile"}
HASH_SUFFIXES = {".sh", ".toml", ".yml", ".yaml", ".cfg", ".ini"}
EXEMPT = {"tools/ocr/data/prompt.txt"}


def tracked_files():
    """!
    @brief The tracked files (or, outside a git checkout, the files found on disk) of the repository.
    @return List of repository-relative POSIX paths.
    """
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [p for p in out.split("\n") if p and (ROOT / p).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and ".venv" not in p.parts]


def kind(rel):
    """!
    @brief The comment syntax a tracked file needs, or None when the file is exempt.
    @param rel Repository-relative POSIX path.
    @return One of "py", "hash", "html" or None.
    """
    p = pathlib.PurePosixPath(rel)
    if rel in EXEMPT or p.parts[0] == ".claude":
        return None
    if p.suffix == ".py":
        return "py"
    if p.suffix in (".html", ".htm"):
        return "html"
    if p.name in HASH_NAMES or p.suffix in HASH_SUFFIXES or (p.name.startswith("requirements") and p.suffix == ".txt"):
        return "hash"
    return None


def python_files():
    """!
    @brief The Python files of the repository that the rule covers (the environments and the working copies of the agents are left out).
    @return Sorted list of pathlib.Path.
    """
    out = []
    for folder in FOLDERS:
        for p in (ROOT / folder).rglob("*.py"):
            parts = set(p.relative_to(ROOT).parts)
            if parts & {".venv", ".venv-research", "__pycache__", "out", "data", "pylib", "variant"}:
                continue
            out.append(p)
    return sorted(out)


def has_header(rel, k):
    """!
    @brief Whether a file starts with the notice in the syntax of its kind.
    @param rel Repository-relative POSIX path.
    @param k   Kind from kind(): "py", "hash" or "html".
    @return True when the notice is where the rule puts it.
    """
    lines = (ROOT / rel).read_text(encoding="utf-8").split("\n")
    if k == "html":
        # The doctype stays the first line so that the page keeps standards mode.
        return len(lines) > 5 and lines[0].lower().startswith("<!doctype") and tuple(lines[1:5]) == HTML_HEADER
    start = 0
    while start < len(lines) and (lines[start].startswith("#!") or (k == "py" and start < 2 and lines[start].startswith("#") and "coding" in lines[start])):
        start += 1
    return tuple(lines[start:start + 2]) == HEADER


def test_every_python_file_starts_with_the_copyright_and_licence_notice():
    missing = []
    for p in python_files():
        lines = p.read_text(encoding="utf-8").split("\n")
        start = 0
        while start < len(lines) and (lines[start].startswith("#!") or (start < 2 and lines[start].startswith("#") and "coding" in lines[start])):
            start += 1
        if tuple(lines[start:start + 2]) != HEADER:
            missing.append(str(p.relative_to(ROOT)))
    assert not missing, "files without the copyright and licence header: " + ", ".join(missing[:10])


def test_every_tracked_source_script_and_config_file_carries_the_notice():
    missing = []
    for rel in tracked_files():
        k = kind(rel)
        if k and not has_header(rel, k):
            missing.append(rel)
    assert not missing, "files without the copyright and licence header (see CLAUDE.md, rule 4): " + ", ".join(missing[:15])
