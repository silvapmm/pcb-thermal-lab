#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_note_similarity.py
@brief ILLUSTRATIVE prototype: does a paper note copy words from the local papers library, and does it obey the template?

Question: how can the 'own words' rule of a paper note be checked mechanically? Two checks:
  1. rules of the note itself (no OCR markers, no images, a word limit for the summary, quotations of at most 25
     words, required fields); they need only the note and can run in CI;
  2. similarity against the local text of the paper (a developer tool: `papers/` is absent in a clean clone, so the
     check says 'skipped' there): the longest run of identical words, and the share of the note's word 6-grams found
     in the paper. Text inside a quotation block (lines starting with '>') is excluded from the run test but is
     counted and length-checked. Numbers, symbols and equations are removed first, because a formula must be allowed
     to match.
A flag is a place for the reviewer to look, not a verdict. Thresholds (run of 8 words, 6-gram share 5 %) are a
first guess to be tuned on the pilot notes; they are not calibrated.

Run (from the repository root):
  .venv/bin/python research/paper-notes-policy/scripts/check_note_similarity.py NOTE.md [--paper PAPER.txt]
"""
import argparse
import re
import sys
from pathlib import Path

RUN_LIMIT = 8          # words in a row identical to the paper (outside a quotation)
SHINGLE = 6            # word n-gram size
SHINGLE_SHARE = 0.05   # share of the note's n-grams found in the paper
QUOTE_LIMIT = 25       # words in one quotation
SUMMARY_LIMIT = 150    # words in the one-paragraph summary
FORBIDDEN = re.compile(r"<!--\s*page\s+\d+|reading_status:\s*machine|!\[[^\]]*\]\(|<img ", re.I)
REQUIRED = ("Key:", "Reading status:", "Licence of the source:", "Summary", "Used in the program")


def words(text):
    """!
    @brief Lower-case words of a text without numbers, symbols, formulas and Markdown marks.

    @param text  Plain or Markdown text.
    @return list[str] Words made of letters only (three or more letters).
    """
    text = re.sub(r"\$[^$]*\$|`[^`]*`", " ", text)           # formulas and code are allowed to match
    return re.findall(r"[a-zà-ÿ]{3,}", text.lower())


def longest_run(note, paper):
    """!
    @brief Longest run of words of the note that also occurs, in the same order, in the paper.

    @param note   Word list of the note.
    @param paper  Word list of the paper.
    @return int Length of the longest common run.
    """
    # Index the paper's words by position; extend every start where the first word matches.
    pos = {}
    for i, w in enumerate(paper):
        pos.setdefault(w, []).append(i)
    best = 0
    for i, w in enumerate(note):
        for j in pos.get(w, ()):
            k = 1
            while i + k < len(note) and j + k < len(paper) and note[i + k] == paper[j + k]:
                k += 1
            best = max(best, k)
    return best


def shingle_share(note, paper, n=SHINGLE):
    """!
    @brief Share of the note's word n-grams that occur in the paper.

    @param note   Word list of the note.
    @param paper  Word list of the paper.
    @param n      n-gram size.
    @return float Share between 0 and 1 (0 when the note is shorter than n).
    """
    grams = {tuple(note[i:i + n]) for i in range(len(note) - n + 1)}
    if not grams:
        return 0.0
    ref = {tuple(paper[i:i + n]) for i in range(len(paper) - n + 1)}
    return len(grams & ref) / len(grams)


def split_note(text):
    """!
    @brief Separate the quotation blocks (lines starting with '>') from the own text.

    @param text  Whole note.
    @return tuple[str, list[str]] Own text and the list of quotations.
    """
    own, quotes = [], []
    for line in text.splitlines():
        if line.startswith("- Citation:"):
            continue            # the bibliographic record (title, venue) is fact and may match the paper
        (quotes if line.lstrip().startswith(">") else own).append(line.lstrip("> ").rstrip())
    return "\n".join(own), quotes


def summary_words(own):
    """!
    @brief Word count of the section headed 'Summary'.

    @param own  Own text of the note.
    @return int Number of words between the heading 'Summary' and the next heading.
    """
    m = re.search(r"^#+\s*Summary.*?\n(.*?)(?=^#+\s|\Z)", own, re.S | re.M)
    return len(re.findall(r"\S+", m.group(1))) if m else -1


def check(text, paper_text=None):
    """!
    @brief Run the rules of the template and, when the paper text is given, the similarity checks.

    @param text        The note.
    @param paper_text  Text of the paper from the local library, or None.
    @return list[str] Flags (empty means no flag).
    """
    flags = []
    if FORBIDDEN.search(text):
        flags.append("forbidden pattern (OCR marker or image)")
    flags += [f"missing field: {r}" for r in REQUIRED if r not in text]
    own, quotes = split_note(text)
    n = summary_words(own)
    if n > SUMMARY_LIMIT:
        flags.append(f"summary has {n} words (limit {SUMMARY_LIMIT})")
    flags += [f"quotation of {len(q.split())} words (limit {QUOTE_LIMIT})" for q in quotes if len(q.split()) > QUOTE_LIMIT]
    if paper_text is not None:
        a, b = words(own), words(paper_text)
        run, share = longest_run(a, b), shingle_share(a, b)
        if run >= RUN_LIMIT:
            flags.append(f"{run} words in a row identical to the paper (limit {RUN_LIMIT - 1})")
        if share > SHINGLE_SHARE:
            flags.append(f"{share:.1%} of the {SHINGLE}-grams occur in the paper (limit {SHINGLE_SHARE:.0%})")
    return flags


def main(argv=None):
    """!
    @brief Command line entry.

    @param argv  Arguments (default: sys.argv).
    @return int 0 when no flag, 1 when flags, 2 on a usage error.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument("note")
    ap.add_argument("--paper", help="text of the paper from the local library (optional)")
    a = ap.parse_args(argv)
    p = Path(a.note)
    if not p.is_file():
        print("no such note", file=sys.stderr)
        return 2
    paper = None
    if a.paper:
        pp = Path(a.paper)
        paper = pp.read_text(errors="ignore") if pp.is_file() else None
    print(f"{p.name}: similarity check {'run' if paper is not None else 'skipped (no local paper text)'}")
    flags = check(p.read_text(), paper)
    for f in flags:
        print("  FLAG:", f)
    if not flags:
        print("  no flag")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
