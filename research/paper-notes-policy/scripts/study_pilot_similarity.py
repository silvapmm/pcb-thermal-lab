#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_pilot_similarity.py
@brief Do the three pilot notes copy words from their papers, and would the checker catch a pasted passage?

Question: for each pilot note of docs/notes-pilot/, the longest run of words shared with the local text of the paper
and the share of the note's word 6-grams found in it (the citation line excluded, then included); then a sensitivity
probe: a run of 40 words taken from the paper (a seeded random position) is pasted into the summary in memory, and
the flags of the checker are printed. Nothing of the paper is written to disk or printed beyond the counts.
The paper texts live in the git-ignored papers library (`--papers`, `PCBT_PAPERS` or `papers/` of the main
checkout); without it the study says so and stops.

Run from the repository root: .venv/bin/python research/paper-notes-policy/scripts/study_pilot_similarity.py
"""
import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_note_similarity as c  # noqa: E402

FOLDER = Path(__file__).resolve().parents[1]
NOTES = FOLDER / "docs" / "notes-pilot"
# Note key -> text of the paper inside the library (the arXiv source of Jaffer, the transcriptions of the others).
PAPERS = {
    "Jaffer2023": "arxiv/2201.02612/2201.02612.md",
    "YovanovichJafarpur1993": "md-final/YovanovichJafarpur1993Bounds.md",
    "Lienhard2024": "md-final/Lienhard2024.md",
}
PASTE_WORDS = 40


def library(arg):
    """!
    @brief Find the papers library.

    @param arg  Path given on the command line, or None.
    @return pathlib.Path|None The folder, or None when it is not found.
    """
    here = Path(__file__).resolve()
    # The parents include the main checkout when the script runs from a worktree under .claude/worktrees/.
    candidates = [arg, os.environ.get("PCBT_PAPERS")] + [str(p / "papers") for p in here.parents]
    for cand in candidates:
        if cand and Path(cand).is_dir() and (Path(cand) / "md-final").is_dir():
            return Path(cand)
    return None


def measure(note_text, paper_text, seed=0):
    """!
    @brief Similarity counts of one note and the flags after a pasted passage.

    @param note_text   The note.
    @param paper_text  Local text of the paper.
    @param seed        Seed of the position of the pasted passage.
    @return dict Counts: words, run, share, run_with_citation, summary_words, flags_pasted.
    """
    own, _ = c.split_note(note_text)
    a, b, a_all = c.words(own), c.words(paper_text), c.words(note_text)
    rng = random.Random(seed)
    i = rng.randrange(len(b) // 10, len(b) - PASTE_WORDS)
    pasted = note_text.replace("## Summary\n\n", "## Summary\n\n" + " ".join(b[i:i + PASTE_WORDS]) + " ", 1)
    return {"words": len(a), "run": c.longest_run(a, b), "share": c.shingle_share(a, b),
            "run_with_citation": c.longest_run(a_all, b), "summary_words": c.summary_words(own),
            "flags": c.check(note_text, paper_text), "flags_pasted": c.check(pasted, paper_text)}


def main(argv=None):
    """!
    @brief Print the table of the three pilot notes.

    @param argv  Arguments (default: sys.argv).
    @return int 0 when every note has no flag and every pasted passage is flagged, 1 otherwise, 2 without the library.
    """
    ap = argparse.ArgumentParser(description="similarity of the pilot notes against the local papers")
    ap.add_argument("--papers", help="papers library folder")
    lib = library(ap.parse_args(argv).papers)
    if lib is None:
        print("papers library not found: set --papers or PCBT_PAPERS (nothing measured)")
        return 2
    ok = True
    print(f"{'note':24s} {'words':>5s} {'run':>4s} {'6-gram':>7s} {'run+cit':>7s} {'summary':>7s}  flags / pasted {PASTE_WORDS} words")
    for key, rel in PAPERS.items():
        r = measure((NOTES / f"{key}.md").read_text(), (lib / rel).read_text(errors="ignore"))
        print(f"{key:24s} {r['words']:5d} {r['run']:4d} {r['share']:7.1%} {r['run_with_citation']:7d} "
              f"{r['summary_words']:7d}  {len(r['flags'])} / {len(r['flags_pasted'])}")
        ok &= not r["flags"] and len(r["flags_pasted"]) > 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
