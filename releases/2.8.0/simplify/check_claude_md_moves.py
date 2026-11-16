#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_claude_md_moves.py
@brief Prove that the simplification of CLAUDE.md lost nothing: every section and every Decisions Log entry of the
       old file is found in the new CLAUDE.md or in the document it was moved to.

Run from the repository root: `.venv/bin/python releases/2.8.0/simplify/check_claude_md_moves.py [--base <ref>]`.
The old file is read with `git show <base>:CLAUDE.md` (default base: the merge base of HEAD and `development`).
The report is printed as Markdown and the exit code is 1 when anything is missing.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# The repository root is three folders above this script (releases/2.8.0/simplify/).
ROOT = Path(__file__).resolve().parents[3]

# Where each old top-level section lives now: (file, heading or text that must exist there).
# A section may have several targets when it was split; every target is checked.
SECTION_TARGETS = {
    "Project Overview": [("CLAUDE.md", "## 1. Project Overview")],
    "Technology Stack": [("CLAUDE.md", "## 2. Technology Stack")],
    "Language and Documentation Rules": [("CLAUDE.md", "## 3. Language and Documentation Rules")],
    "Conventions": [("CLAUDE.md", "## 4. Conventions")],
    "Licences": [("CLAUDE.md", "## 5. Licences")],
    "Git Workflow": [("CLAUDE.md", "### Git Workflow")],
    "Git Language and Naming": [("CLAUDE.md", "### Git Language and Naming")],
    "Project Structure": [("CLAUDE.md", "## 13. Project Structure"),
                          ("docs/models.md", "## Appendix: module map (detailed)")],
    "Why the legacy solvers were replaced": [("CLAUDE.md", "why its solvers were replaced: `docs/validation.md` 6"),
                                             ("docs/validation.md", "## 6.")],
    "Commands": [("CLAUDE.md", "## 14. Commands")],
    "Branches and Versions": [("CLAUDE.md", "### Branches and Versions")],
    "Git Policy": [("CLAUDE.md", "### Git Policy")],
    "Papers library and OCR": [("CLAUDE.md", "## 7. Papers library and OCR")],
    "Local boards library": [("CLAUDE.md", "## 8. Local boards library")],
    "Research branches": [("CLAUDE.md", "## 9. Research branches")],
    "Before every commit: update the documentation (mandatory)":
        [("CLAUDE.md", "## 10. Before every commit: update the documentation (mandatory)")],
    "Maintaining This File": [("CLAUDE.md", "## 16. Maintaining This File")],
    "Claude Code Settings": [("CLAUDE.md", "### Claude Code Settings")],
    "Agents and workflow": [("CLAUDE.md", "## 12. Agents and workflow")],
    "Where to continue (2.8.0)": [("CLAUDE.md", "## 15. Where to continue (2.8.0)")],
    "Decisions Log": [("docs/decisions-log.md", "# Decisions Log")],
}

# Rules whose words were dictated by the maintainer or that a test or an agent quotes: they must stay verbatim.
VERBATIM_RULES = [
    "something that must exist and be a RULE is putting that header, the one that mentions me and the licence, in ALL files",
    "#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.",
    "#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.",
    "Work branches are never deleted, locally or on the remote: they stay as the record of the work.",
    "The key is never printed, logged, put in a command line or a URL, or written in an exception, a report or a test output",
    "A transcription counts as READ only after the reviewer compares it with the page image",
    "no commit without updating, in the same commit, every file the change touches.",
    "Literature check (the sources are opened and the published cases are reproduced)",
    "When an investigation is closed (or a closed one is reopened and corrected) the reviewer must review it and update it",
    "Reports to the maintainer are short and in plain Portuguese",
    "QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread",
    "Pages go online to Google (Gemini) by the maintainer's decision",
]

# New standing rules of this session that must now be in CLAUDE.md.
NEW_RULES = [
    "The FEM is a program model", "The surface read-out is a VIEW, never a mode",
    "The theory is explicit and self-contained", "Numbers name their tree and their reference",
    "every number the user sees carries the name of its read-out",
    "A model correction moves numbers only through pending files",
    "The whole battery runs with the real-board environment PROVEN loaded",
    "A tester that cannot wait inside its session is resumed",
]


def git_show(ref: str, path: str) -> str:
    """!
    @brief Read a file as it is at a git revision.

    @param ref   The git revision (commit, branch or tag).
    @param path  The path of the file, relative to the repository root.

    @return str The content of the file at that revision.
    """
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def sections(text: str) -> list:
    """!
    @brief List the headings of levels two and three of a Markdown text.

    @param text  The Markdown text.

    @return list Heading titles without the leading hashes, in order.
    """
    return [m.group(2).strip() for m in re.finditer(r"^(##|###) (.+)$", text, re.M)]


def log_entries(text: str) -> list:
    """!
    @brief Split the Decisions Log of the old CLAUDE.md into entries.

    An entry is a line that starts with '- ' plus the indented lines that follow it; a non-blank line that is not a
    bullet (the instruction line in the middle of the log) is an entry of its own.

    @param text  The whole old CLAUDE.md.

    @return list The entries as exact strings.
    """
    body = text.split("\n## Decisions Log\n", 1)[1]
    entries, cur = [], None
    for line in body.split("\n"):
        if line.startswith("- "):
            if cur is not None:
                entries.append("\n".join(cur))
            cur = [line]
        elif line.startswith("  ") and cur is not None:
            cur.append(line)
        else:
            if cur is not None:
                entries.append("\n".join(cur))
                cur = None
            if line.strip():
                entries.append(line)
    if cur is not None:
        entries.append("\n".join(cur))
    return entries


def main() -> int:
    """!
    @brief Run every check and print the Markdown report.

    @return int 0 when nothing is missing, 1 otherwise.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None, help="revision of the old CLAUDE.md (default: merge base with development)")
    args = ap.parse_args()
    base = args.base or subprocess.run(["git", "merge-base", "HEAD", "development"], cwd=ROOT, check=True,
                                       capture_output=True, text=True).stdout.strip()
    old = git_show(base, "CLAUDE.md")
    files = {p: (ROOT / p).read_text() for p in ("CLAUDE.md", "docs/decisions-log.md", "docs/models.md",
                                                 "docs/versions.md", "docs/validation.md")}
    new = files["CLAUDE.md"]
    missing = []
    out = [f"# CLAUDE.md moves: check against `{base[:12]}`", "",
           f"Old CLAUDE.md: {len(old.splitlines())} lines, {len(old.encode())} bytes. "
           f"New CLAUDE.md: {len(new.splitlines())} lines, {len(new.encode())} bytes. "
           f"docs/decisions-log.md: {len(files['docs/decisions-log.md'].encode())} bytes.", "",
           "## 1. Sections of the old file and where they are now", "", "| Old section | Now in | Found |",
           "| :-- | :-- | :-- |"]
    for title in sections(old):
        targets = SECTION_TARGETS.get(title)
        if targets is None:
            missing.append(f"section without a target: {title}")
            out.append(f"| {title} | (no target) | NO |")
            continue
        for path, needle in targets:
            ok = needle in files[path]
            if not ok:
                missing.append(f"{title} -> {path}: {needle}")
            out.append(f"| {title} | `{path}`: {needle.replace('|', '/')} | {'yes' if ok else 'NO'} |")
    # The Decisions Log entries, each byte-identical in the new document.
    entries = log_entries(old)
    log = files["docs/decisions-log.md"]
    lost = [e for e in entries if e not in log]
    missing += [f"log entry not found: {e[:80]}" for e in lost]
    out += ["", "## 2. Decisions Log entries", "",
            f"{len(entries)} entries in the old log (bullets with their continuation lines, and the instruction line); "
            f"{len(entries) - len(lost)} found byte-identical in `docs/decisions-log.md`; {len(lost)} missing."]
    # The order is kept: the entries appear in the same order in the new document.
    pos, ordered = -1, True
    for e in entries:
        p = log.find(e, pos + 1)
        if p < pos:
            ordered = False
        pos = max(pos, p)
    out.append(f"Order of the entries kept: {'yes' if ordered else 'NO'}.")
    if not ordered:
        missing.append("log order changed")
    # The structure block: every line moved verbatim to the appendix of docs/models.md, the test history to versions.md.
    block = old.split("## Project Structure\n", 1)[1].split("\n## ", 1)[0]
    lines = [ln for ln in block.split("\n") if ln.strip() and not ln.startswith("```")]
    tests_line = [ln for ln in lines if ln.startswith("tests/ ")]
    other = [ln for ln in lines if not ln.startswith("tests/ ")]
    gone = [ln for ln in other if ln not in files["docs/models.md"]]
    missing += [f"structure line not in models.md: {ln[:60]}" for ln in gone]
    hist = tests_line[0].split("pytest suite (", 1)[1][:-1] if tests_line else ""
    hist_ok = bool(hist) and hist in files["docs/versions.md"]
    if not hist_ok:
        missing.append("test-count history not in docs/versions.md")
    out += ["", "## 3. Project structure and the test-count history", "",
            f"{len(other)} lines of the old structure block (text and code block); {len(other) - len(gone)} found "
            f"verbatim in `docs/models.md` (appendix); test-count history ({len(hist)} characters) verbatim in "
            f"`docs/versions.md` 'How each version was tested': {'yes' if hist_ok else 'NO'}."]
    # The commands: every command of the old block is still a command of the new block (comments may be shorter).
    cmd_old = [ln.split("  #")[0].strip() for ln in old.split("## Commands", 1)[1].split("```")[1].split("\n") if ln.strip() and ln.strip() != "sh"]
    cmd_lost = [c for c in cmd_old if c not in new]
    missing += [f"command lost: {c}" for c in cmd_lost]
    out += ["", "## 4. Commands", "", f"{len(cmd_old)} commands in the old file; {len(cmd_old) - len(cmd_lost)} still in CLAUDE.md."]
    # Verbatim rules and the new rules.
    out += ["", "## 5. Rules kept verbatim and new standing rules", "", "| Text | In CLAUDE.md |", "| :-- | :-- |"]
    for needle in VERBATIM_RULES + NEW_RULES:
        ok = needle in new
        if not ok:
            missing.append(f"rule text missing: {needle}")
        out.append(f"| {needle.replace('|', '/')} | {'yes' if ok else 'NO'} |")
    out += ["", "## 6. Result", "", "Nothing is missing." if not missing else "Missing:\n\n" + "\n".join(f"- {m}" for m in missing)]
    print("\n".join(out))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
