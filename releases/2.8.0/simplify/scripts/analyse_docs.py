#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analyse_docs.py
@brief Measure the size, the duplication and the history text of the project documents (input of DOCS_PLAN.md).

@details Run from the repository root: `.venv/bin/python releases/2.8.0/simplify/scripts/analyse_docs.py`.
It prints, for every document: lines, KB, sentences, the share of its long sentences (at least 60 characters
after normalisation) that also occur in another document, the share of its precise numbers (at least three
significant digits, or a signed percentage) that also occur in another document, and the lines that carry a
version number or a history phrase ('was', 'used to', 'before 2.x', 'now ...'). Nothing is written.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

# The repository root is three folders above this script (releases/2.8.0/simplify/scripts)
ROOT = Path(__file__).resolve().parents[4]

# The documents of the project (the research READMEs are counted only in total)
DOCS = ["README.md", "CHANGELOG.md", "docs/theory.md", "docs/models.md", "docs/validation.md", "docs/versions.md",
        "docs/calculators.md", "docs/research.md", "pcbthermal/help/index.html", "pcbthermal/help/calculator.html",
        "research/README.md"]

# A version number of the program (2.4.5, 2.6.0, ...) marks a history statement in a document of the present
VERSION = re.compile(r"\b2\.[0-9]\.[0-9]\b")
# Phrases that describe a former state of the program
HISTORY = re.compile(r"\b(used to|was (?:then|before|replaced|changed|removed)|before (?:the|2\.)|earlier (?:text|tree|code|version)"
                     r"|superseded|withdrawn|no longer|is now|now (?:uses|reads|takes|has))\b", re.I)
# A precise number: three significant digits or more, or a signed percentage
NUMBER = re.compile(r"[-+−]?\d+\.\d{2,}|[-+−]\d+(?:\.\d+)? ?%")


def plain_text(path: Path) -> str:
    """!
    @brief Read a document as plain text (HTML tags removed).

    @param path  Path of the document.
    @return str The text, with the tags of an HTML file replaced by spaces.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        # Tags carry no content of their own; entities are rare enough to keep
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def sentences(text: str) -> list:
    """!
    @brief Split a text into normalised sentences of at least 60 characters.

    @param text  Plain text of a document.
    @return list The normalised sentences (lower case, markup and spaces collapsed).
    """
    # Markdown emphasis, code ticks and table bars are not content
    flat = re.sub(r"[`*_|#>]", " ", text)
    parts = re.split(r"(?<=[.;:])\s+|\n\s*\n", flat)
    out = []
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip().lower()
        if len(s) >= 60:
            out.append(s)
    return out


def main() -> int:
    """!
    @brief Print the table of sizes, duplication and history lines.

    @return int Exit code 0.
    """
    texts = {d: plain_text(ROOT / d) for d in DOCS}
    sents = {d: sentences(t) for d, t in texts.items()}
    nums = {d: set(NUMBER.findall(t)) for d, t in texts.items()}
    # Where each sentence and number occurs
    where_s, where_n = defaultdict(set), defaultdict(set)
    for d in DOCS:
        for s in sents[d]:
            where_s[s].add(d)
        for n in nums[d]:
            where_n[n].add(d)
    print(f"{'document':34s} {'lines':>6s} {'KB':>5s} {'sent':>5s} {'dupS%':>6s} {'selfS%':>6s} {'nums':>5s} {'dupN%':>6s} {'verL':>5s} {'histL':>5s}")
    tot_s = tot_dup = 0
    for d in DOCS:
        raw = (ROOT / d).read_text(encoding="utf-8")
        lines = raw.splitlines()
        ss = sents[d]
        dup = sum(1 for s in ss if len(where_s[s]) > 1)
        # Sentences repeated inside the same document
        self_dup = len(ss) - len(set(ss))
        nd = sum(1 for n in nums[d] if len(where_n[n]) > 1)
        ver = sum(1 for ln in lines if VERSION.search(ln))
        hist = sum(1 for ln in lines if HISTORY.search(ln))
        tot_s += len(ss)
        tot_dup += dup
        print(f"{d:34s} {len(lines):6d} {len(raw.encode()) // 1024:5d} {len(ss):5d} {100 * dup / max(len(ss), 1):6.1f} "
              f"{100 * self_dup / max(len(ss), 1):6.1f} {len(nums[d]):5d} {100 * nd / max(len(nums[d]), 1):6.1f} {ver:5d} {hist:5d}")
    print(f"all long sentences {tot_s}, in two or more documents {tot_dup} ({100 * tot_dup / tot_s:.1f} %)")
    # The pairs that share the most sentences
    pairs = defaultdict(int)
    for s, ds in where_s.items():
        ds = sorted(ds)
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                pairs[(ds[i], ds[j])] += 1
    print("pairs sharing sentences:")
    for (a, b), n in sorted(pairs.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {n:4d}  {a} <-> {b}")
    # Paraphrase is caught better by runs of eight words than by whole sentences
    grams = {d: shingles(texts[d]) for d in DOCS}
    print("share of the 8-word runs of a document found in another document, and precise numbers also in validation.md:")
    for d in DOCS:
        others = set().union(*[grams[o] for o in DOCS if o != d])
        in_val = len(nums[d] & nums["docs/validation.md"]) if d != "docs/validation.md" else 0
        print(f"  {d:34s} {100 * len(grams[d] & others) / max(len(grams[d]), 1):5.1f} %   numbers {len(nums[d]):4d}, in validation {in_val:4d}")
    return 0


def shingles(text: str, k: int = 8) -> set:
    """!
    @brief The set of runs of k consecutive words of a text.

    @param text  Plain text of a document.
    @param k     Number of words in a run.
    @return set Tuples of k words (lower case, markup removed).
    """
    w = re.findall(r"[a-z0-9.%+\-−]+", re.sub(r"[`*_|#>()\[\]]", " ", text).lower())
    return {tuple(w[i:i + k]) for i in range(len(w) - k)}


if __name__ == "__main__":
    sys.exit(main())
