#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file theory2_moves.py
@brief Apply and check the second pass of the simplification of docs/theory.md (branch docs/simplify-theory-2).

@details The edits are listed in `theory2_moves.json`; every one is resolved against the text of the BASE commit and
the edits before it, never against the working tree. An edit replaces the span of `docs/theory.md` that begins with
the text `start` and ends with the text `end` (both included, `start` found once) by `new`, which keeps the law, the
range, the direction of the error, the warnings, the sources and one representative number, and points to the
validation sections in `point` (list of `[file, section]`, file `validation.md` or `validation-history.md`).
* A number that leaves the theory must exist in one of the pointed sections (compared without the sign, as a token).
* An edit with `move: true` is also written, byte for byte, into `docs/validation-history.md`, in the block that this
  script appends at its end under the theory section number; its numbers are then kept by the history itself.

Run from the repository root:
* `theory2_moves.py apply`: write `docs/theory.md` and `docs/validation-history.md` from the base and the edits.
* `theory2_moves.py report`: the same without writing; prints, per edit, the numbers that are not in the pointed
  sections (the work list while the edits are drafted).
* `theory2_moves.py check`: compare both documents AT HEAD (read with `git show HEAD:...`, spec included) with what
  the edits produce from the base, and check the numbers of every edit.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SPEC = "releases/2.9.0/simplify/theory2_moves.json"
THEORY = "docs/theory.md"
VALID = "docs/validation.md"
VHIST = "docs/validation-history.md"
HIST_TITLE = "## Theory passages moved by the second simplification"


def git_show(rev, path):
    """!
    @brief Read a tracked file at a commit.

    @param rev   Commit, tag or `HEAD`.
    @param path  Path of the file relative to the repository root.

    @return str Text of the file at that commit.
    """
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True, text=True,
                          check=True).stdout


def tokens(text):
    """!
    @brief Numeric tokens of a text, without sign.

    @param text  Document text.

    @return collections.Counter Token to count.
    """
    pat = r"\d+(?:[.,]\d+)?(?:e[+-]?\d+)?"
    return Counter(x.replace(",", ".") for x in re.findall(pat, text))


def section_text(doc, number):
    """!
    @brief Text of a validation section, with its subsections.

    @param doc     Text of a validation document.
    @param number  Section number as written in the heading, such as `36` or `21.2`.

    @return str Text from the heading to the next heading of the same or a higher level.
    """
    level = number.count(".") + 2  # `## 36.` is level 2, `### 21.2` level 3
    m = re.search(rf"^#{{{level}}} {re.escape(number)}[ .]", doc, re.M)
    if not m:
        raise SystemExit(f"section {number} not found")
    nxt = re.search(rf"^#{{2,{level}}} ", doc[m.end():], re.M)
    return doc[m.start(): m.end() + (nxt.start() if nxt else len(doc))]


def build(base_theory, base_hist, spec, docs):
    """!
    @brief Produce the new theory and history from the base and the edits.

    @param base_theory  Text of `docs/theory.md` at the base commit.
    @param base_hist    Text of `docs/validation-history.md` at the base commit.
    @param spec         Parsed `theory2_moves.json`.
    @param docs         Dict file name to text of `validation.md` and `validation-history.md` (base).

    @return tuple (theory text, history text, list of (edit, missing numbers)).
    """
    theory, moved, report = base_theory, [], []
    for ed in spec["edits"]:
        text = theory
        if text.count(ed["start"]) != 1:
            raise SystemExit(f"start found {text.count(ed['start'])} times: {ed['start'][:60]!r}")
        b = text.index(ed["start"])
        e = text.find(ed["end"], b)
        if e < 0:
            raise SystemExit(f"end not found after {ed['start'][:60]!r}")
        e += len(ed["end"])
        old = text[b:e]
        theory = text[:b] + ed["new"] + text[e:]
        if ed.get("move"):
            moved.append((ed["sec"], ed["label"], old))
        pool = Counter()
        for fname, num in ed.get("point", []):
            pool += tokens(section_text(docs[fname], num))
        gone = tokens(old) - tokens(ed["new"])
        missing = {k: v for k, v in gone.items() if k not in pool}
        report.append((ed, {} if ed.get("move") else missing))
    hist = base_hist
    if moved:
        hist = hist.rstrip("\n") + f"\n\n{HIST_TITLE}\n\nParagraphs and sentences of `theory.md` that held measured numbers " \
            "which the validation does not hold in the same form. They were moved here byte for byte, under the " \
            "number of the section they left; the theory keeps the law and one representative number and points here. " \
            "The list and its check are `releases/2.9.0/simplify/theory2_moves.json` and " \
            "`releases/2.9.0/simplify/scripts/theory2_moves.py`.\n"
        for sec in sorted({s for s, _, _ in moved}, key=lambda s: [int(x) if x.isdigit() else 0 for x in re.split(r"[.a]", s)]):
            hist += f"\n### Theory {sec}\n"
            for s, label, old in moved:
                if s == sec:
                    hist += f"\n**{label}**\n\n> {old}\n"
    return theory, hist, report


def main():
    """!
    @brief Command line entry point.

    @return int Exit code, 1 when a check fails.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["apply", "report", "check"])
    args = ap.parse_args()
    if args.mode == "check":
        spec = json.loads(git_show("HEAD", SPEC))
    else:
        spec = json.loads((ROOT / SPEC).read_text())
    base = spec["base"]
    bt, bh = git_show(base, THEORY), git_show(base, VHIST)
    docs = {"validation.md": git_show(base, VALID), "validation-history.md": bh}
    theory, hist, report = build(bt, bh, spec, docs)
    ok = True
    for ed, missing in report:
        if missing:
            ok = False
            print(f"MISSING in {ed['point']}: {ed['label'][:50]!r}: {missing}")
    if args.mode == "apply":
        (ROOT / THEORY).write_text(theory)
        (ROOT / VHIST).write_text(hist)
        print("written theory", len(theory), "history", len(hist), "bytes (characters)")
        return 0 if ok else 1
    if args.mode == "report":
        print(f"{len(report)} edits; theory {len(bt)} -> {len(theory)} characters; ok={ok}")
        return 0 if ok else 1
    for name, got, want in [(THEORY, git_show("HEAD", THEORY), theory), (VHIST, git_show("HEAD", VHIST), hist)]:
        same = got == want
        ok &= same
        print(f"{name} at HEAD equals base + edits: {same}")
    # the validation document itself must be the base one (the pointed sections are not edited)
    same = git_show("HEAD", VALID) == docs["validation.md"]
    ok &= same
    print(f"{VALID} at HEAD equals base: {same}")
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
