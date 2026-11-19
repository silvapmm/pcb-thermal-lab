#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file theory_moves.py
@brief Apply and check the moves of the simplification of docs/theory.md (branch docs/simplify-theory).

@details The moves are listed in `theory_moves.json`. Three kinds of edit, all resolved against the text of the BASE
commit (10757a0e), never against the working tree:
* `moves`: a span of `docs/theory.md` (from the text `start` to the text `end`, both included) that is history or a
  superseded value; it leaves the theory byte for byte and is written, unchanged, into `docs/theory-history.md`
  under its section number; `replace` is what stays in its place (usually nothing);
* `splits`: a paragraph is cut in two before the text `before` (only whitespace changes; the check compares the
  text without whitespace);
* `intro`: the one sentence of the introduction that points to the history file;
* `edits`: a correction of the current text found by the review of the branch (an exact text, found once, replaced by
  another; each says why), applied after the splits; the number check still covers them.

Run from the repository root:
* `theory_moves.py apply`: write the two documents from the base commit and the moves.
* `theory_moves.py check`: compare the two documents AT HEAD (read with `git show HEAD:...`, not the working tree)
  with what the moves produce from the base, and check the numbers of the theory and its history against the base.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SPEC = ROOT / "releases" / "2.9.0" / "simplify" / "theory_moves.json"
THEORY = "docs/theory.md"
HISTORY = "docs/theory-history.md"

HISTORY_HEAD = """# Theory: history

Passages of `docs/theory.md` that describe an earlier state of the program or a value that was replaced, kept as
the record. They were moved here byte for byte, each under the number of the section it left, and the theory
keeps only what is implemented now. What each version did is in `versions.md`; the current numbers are in
`validation.md`. The list of moves and its check are `releases/2.9.0/simplify/theory_moves.json` and
`releases/2.9.0/simplify/scripts/theory_moves.py`.
"""


def git_show(rev, path):
    """!
    @brief Read a tracked file at a commit.

    @param rev   Commit, tag or `HEAD`.
    @param path  Path of the file relative to the repository root.

    @return str Text of the file at that commit.
    """
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True, text=True,
                          check=True).stdout


def resolve(text, start, end):
    """!
    @brief Find the span that begins with `start` and ends with `end`.

    @param text   Document text.
    @param start  Exact beginning of the span (must occur once).
    @param end    Exact end of the span (first occurrence after the start).

    @return tuple (begin, stop) offsets of the span, `stop` after the last character of `end`.
    """
    if text.count(start) != 1:
        raise SystemExit(f"start text found {text.count(start)} times: {start[:60]!r}")
    b = text.index(start)
    e = text.find(end, b)
    if e < 0:
        raise SystemExit(f"end text not found after {start[:60]!r}")
    return b, e + len(end)


def build(base_theory, spec):
    """!
    @brief Produce the new theory and the new history from the base theory and the moves.

    @param base_theory  Text of `docs/theory.md` at the base commit.
    @param spec         Parsed `theory_moves.json`.

    @return tuple (theory text, history text).
    """
    theory = base_theory
    entries = []
    for mv in spec["moves"]:
        b, e = resolve(theory, mv["start"], mv["end"])
        entries.append((mv["sec"], mv["label"], theory[b:e]))
        theory = theory[:b] + mv.get("replace", "") + theory[e:]
    if spec.get("intro_old"):
        if theory.count(spec["intro_old"]) != 1:
            raise SystemExit("intro text not unique")
        theory = theory.replace(spec["intro_old"], spec["intro_new"])
    for sp in spec["splits"]:
        key = " " + sp["before"]
        if theory.count(key) != 1:
            raise SystemExit(f"split text found {theory.count(key)} times: {sp['before'][:60]!r}")
        theory = theory.replace(key, "\n\n" + sp.get("indent", "") + sp["before"])
    for ed in spec.get("edits", []):
        # A correction of the current text (review of the branch): the old text must be found exactly once
        if theory.count(ed["old"]) != 1:
            raise SystemExit(f"edit text found {theory.count(ed['old'])} times: {ed['old'][:60]!r}")
        theory = theory.replace(ed["old"], ed["new"])
    # the history is ordered by the section number, then by the order of the moves
    def sec_key(s):
        return [int(x) if x.isdigit() else 0 for x in re.split(r"[.]", s.replace("a", ".0"))]
    out = [HISTORY_HEAD]
    for sec in sorted({s for s, _, _ in entries}, key=sec_key):
        out.append(f"\n## {sec}\n")
        for s, label, span in entries:
            if s == sec:
                out.append(f"\n**{label}**\n\n> {span}\n")
    return theory, "".join(out)


def numbers(text):
    """!
    @brief Count the numeric tokens of a text.

    @param text  Document text.

    @return collections.Counter Token to count (sign and decimal comma normalised).
    """
    pat = r"[-+−]?\d+(?:[.,]\d+)?(?:e[+-]?\d+)?"
    return Counter(x.replace("−", "-").lstrip("+") for x in re.findall(pat, text))


def main():
    """!
    @brief Command line entry point.

    @return int Exit code, 1 when a check fails.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["apply", "check"])
    args = ap.parse_args()
    spec = json.loads(SPEC.read_text())
    base = git_show(spec["base"], THEORY)
    theory, history = build(base, spec)
    if args.mode == "apply":
        (ROOT / THEORY).write_text(theory)
        (ROOT / HISTORY).write_text(history)
        print("written", len(theory), "and", len(history), "characters")
        return 0
    ok = True
    head_t, head_h = git_show("HEAD", THEORY), git_show("HEAD", HISTORY)
    for name, got, want in [(THEORY, head_t, theory), (HISTORY, head_h, history)]:
        same = got == want
        ok &= same
        print(f"{name} at HEAD equals base + moves: {same}")
    # whitespace-only check of the splits, and byte-for-byte presence of every moved span
    for mv in spec["moves"]:
        b, e = resolve(base, mv["start"], mv["end"])
        if f"> {base[b:e]}\n" not in head_h:
            ok = False
            print("moved span missing from the history:", mv["start"][:60])
    base_n = numbers(base)
    now_n = numbers(head_t) + numbers(head_h)
    lost = {k: base_n[k] - now_n[k] for k in base_n if now_n[k] < base_n[k]}
    print(f"numeric tokens: base {sum(base_n.values())}; theory + history at HEAD {sum(now_n.values())}; "
          f"kinds lost {len(lost)}")
    if lost:
        ok = False
        print("lost:", sorted(lost.items(), key=lambda x: -x[1])[:30])
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
