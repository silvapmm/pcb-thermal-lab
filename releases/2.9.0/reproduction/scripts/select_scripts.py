#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file select_scripts.py
@brief Derive mechanically the study scripts the 2.9.0 reproduction pass compares (DECISION.md 1).

@details A script of `research/*/scripts/` (the same set as `repro_scripts.sh`: no `make_figures`, `make_diagrams`
or `_private` helper) is AFFECTED when its text, or the text of its folder's `lib/` when the script mentions `lib`,
reaches a path whose numbers 2.9.0 moves on purpose: T the FVM/FDM/FEM time stepping (default Crank-Nicolson with
quarter first frames), F the FEM (thin copper source, transient), SB the 3D solid with a metal block, heatsink or copper slab
named in the text (interface pad in-plane, copper slabs), S any other 3D-solid use (expected bit-identical, checked because the module
changed). Every folder with no affected script gives one sample script (its first `study_*.py`, else its first
script) to prove that the unaffected folders did not shift. Output: a TSV `folder<TAB>script<TAB>class`, in the
order of the run (T, F, SB, S, sample), and the counts on standard error.
"""
import pathlib
import re
import sys

T_RE = re.compile(r"solve_transient|transient_from_network|\.transient\(|run_profile|animation|Animation")
F_RE = re.compile(r"\bfem\b|femcore|femmesh|[\"']fem[\"']")
S_RE = re.compile(r"solid3d")
SB_RE = re.compile(r"[Bb]lock|[Hh]eatsink|copper_slab")
SKIP_RE = re.compile(r"^(make_figures|make_diagrams|_[a-z_]*)\.py$")
ORDER = ("T", "F", "SB", "S", "sample")


def classify(text):
    """!
    @brief Give the class of one script from its text (and its folder's lib text).

    @param text  Source text of the script, plus its folder's lib/ when the script uses it.

    @return str One of "T", "F", "SB", "S" (the first that applies, in the order of the run) or "" if unaffected.
    """
    # The first match wins, so a transient FEM script runs in the first (transient) group
    if T_RE.search(text):
        return "T"
    if F_RE.search(text):
        return "F"
    if S_RE.search(text):
        return "SB" if SB_RE.search(text) else "S"
    return ""


def select(root):
    """!
    @brief List the scripts of the pass with their class.

    @param root  Path of the repository tree under test.

    @return list Tuples (folder, script name, class) in the order of the run.
    """
    rows = []
    for sc in sorted(pathlib.Path(root).glob("research/*/scripts/*.py")):
        if SKIP_RE.match(sc.name):
            continue
        text = sc.read_text(errors="ignore")
        # A script that imports its folder's lib/ inherits what the lib calls
        if "lib" in text:
            for lib in sorted((sc.parent.parent / "lib").glob("*.py")):
                text += lib.read_text(errors="ignore")
        rows.append((sc.parts[-3], sc.name, classify(text)))
    affected_folders = {f for f, _, c in rows if c}
    sample = {}
    # One sample per unaffected folder: its first study_*.py, else its first script
    for f, n, _ in rows:
        if f not in affected_folders and f not in sample and n.startswith("study"):
            sample[f] = n
    for f, n, _ in rows:
        if f not in affected_folders and f not in sample:
            sample[f] = n
    chosen = [r for r in rows if r[2]] + [(f, n, "sample") for f, n in sorted(sample.items())]
    return sorted(chosen, key=lambda r: (ORDER.index(r[2]), r[0], r[1]))


def main():
    """!
    @brief Print the TSV of the selected scripts and the counts per class.

    @return int Exit code 0.
    """
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    chosen = select(root)
    for f, n, c in chosen:
        sys.stdout.write(f"{f}\t{n}\t{c}\n")
    counts = {c: sum(1 for r in chosen if r[2] == c) for c in ORDER}
    sys.stderr.write(f"selected {len(chosen)}: {counts}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
