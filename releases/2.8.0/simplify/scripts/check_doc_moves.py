#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_doc_moves.py
@brief Move blocks of a document to another document byte for byte, and prove that nothing was lost.

@details Each move takes the BODY of a section (the text strictly between its heading line and the next heading
line) out of a source document, puts the heading and the body unchanged into a destination document, and leaves
in the source the heading and one pointer line. The table of moves is `MOVES` below and `DOC_MOVES.md`.

Run from the repository root:
* `.venv/bin/python releases/2.8.0/simplify/scripts/check_doc_moves.py`: the check (exit code 1 on any loss). It
  verifies that every moved body is in the destination byte for byte, that the source holds the heading and the
  pointer and no longer the body, and, with `--base <commit>`, that putting the bodies back into the source gives
  the source of that commit exactly (valid until another branch changes the source; the first checks stay valid).
* `--apply --base <commit>`: perform the moves on the source of `<commit>` (used once, on the branch
  `docs/simplify-docs-plan`; it refuses when the destination exists already).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# The repository root is four folders above this script (releases/2.8.0/simplify/scripts)
ROOT = Path(__file__).resolve().parents[4]

# One entry per moved body: the source, the destination, the exact heading line of the section whose body moves
# and the GitHub anchor of that heading in the destination (used by the pointer line).
MOVES = [
    ("docs/validation.md", "docs/validation-history.md",
     "## 6. The removed wxPython program against the current one",
     "6-the-removed-wxpython-program-against-the-current-one"),
    ("docs/validation.md", "docs/validation-history.md",
     "## 20. Corrections found in a review of the models",
     "20-corrections-found-in-a-review-of-the-models"),
    ("docs/validation.md", "docs/validation-history.md",
     "## 21. One-layer boards and the rings of the Lumped model (second round of the review)",
     "21-one-layer-boards-and-the-rings-of-the-lumped-model-second-round-of-the-review"),
    ("docs/validation.md", "docs/validation-history.md",
     "### 21.1 The error of the 2-layer boards (documented here; corrected for the FVM by the laminate nodes of section 21.2)",
     "211-the-error-of-the-2-layer-boards-documented-here-corrected-for-the-fvm-by-the-laminate-nodes-of-section-212"),
]

# The text that opens the destination document (written by --apply)
HISTORY_HEAD = """# Validation: history

The sections of `docs/validation.md` that describe the program of an earlier version and are no longer kept
current. They were moved here byte for byte (the heading and the whole body of each section; the move and its
check are `releases/2.8.0/simplify/DOC_MOVES.md` and `releases/2.8.0/simplify/scripts/check_doc_moves.py`). The
numbering is that of `docs/validation.md`, where each heading stays with a pointer to this file, so a reference
such as 'validation 20' still finds its place. The current numbers are in `docs/validation.md`.

| Section | Why it is history |
| :-- | :-- |
| 6 | the removed wxPython program against the program of 2.4.5 (the reason the legacy solvers were replaced) |
| 20 | the corrections of the first model review, with the tables of the program before 2.4.5 |
| 21 (body before 21.1) | the second round of that review (2.4.x); the current laminate rule is 21.2, the 3D slabs 21.3 |
| 21.1 | the error of the 2-layer boards before the laminate rule of 21.2 (marked superseded by the 2.8.0 audit) |

"""


def pointer(anchor: str) -> str:
    """!
    @brief The line left in the source in place of a moved body.

    @param anchor  GitHub anchor of the heading in the destination document.
    @return str The pointer paragraph, with a blank line before and after.
    """
    return (f"\n*History, not kept current: the body of this section was moved byte for byte to "
            f"[validation-history.md](validation-history.md#{anchor}).*\n\n")


def split_body(text: str, heading: str):
    """!
    @brief Find the body of a section: the text strictly between its heading line and the next heading line.

    @param text     The whole document.
    @param heading  The exact heading line (without the newline).
    @return tuple (start, end) character offsets of the body in the text.
    @throws ValueError If the heading is not found exactly once or has no following heading.
    """
    key = heading + "\n"
    if text.count("\n" + key) != 1:
        raise ValueError(f"heading not found exactly once: {heading!r}")
    start = text.index("\n" + key) + 1 + len(key)
    # The next heading line of any level ends the body
    nxt = text.find("\n#", start - 1)
    if nxt < 0:
        raise ValueError(f"no heading after {heading!r}")
    return start, nxt + 1


def git_show(commit: str, rel: str) -> str:
    """!
    @brief The content of a file at a commit.

    @param commit  A commit name.
    @param rel     Path relative to the repository root.
    @return str The file text.
    """
    return subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout


def apply(base: str) -> None:
    """!
    @brief Perform the moves on the sources of a commit and write the source and destination documents.

    @param base  The commit whose sources are moved.
    @throws SystemExit If a destination exists already.
    """
    sources = {}
    dests = {}
    for src, dst, heading, anchor in MOVES:
        if dst not in dests and (ROOT / dst).exists():
            sys.exit(f"{dst} exists already: --apply is used once")
        text = sources.setdefault(src, git_show(base, src))
        a, b = split_body(text, heading)
        body = text[a:b]
        # The destination gets the heading and the body unchanged
        dests[dst] = dests.get(dst, HISTORY_HEAD) + heading + "\n" + body
        sources[src] = text[:a] + pointer(anchor) + text[b:]
    for rel, text in list(sources.items()) + list(dests.items()):
        (ROOT / rel).write_text(text, encoding="utf-8")


def check(base: str | None) -> list:
    """!
    @brief Verify the moves against the working tree (and, with a base, against the sources of that commit).

    @param base  A commit whose sources must be reconstructed exactly, or None.
    @return list Problems found (empty when nothing was lost).
    """
    problems = []
    restored = {}
    for src, dst, heading, anchor in MOVES:
        cur = (ROOT / src).read_text(encoding="utf-8")
        dest = (ROOT / dst).read_text(encoding="utf-8")
        if base is None:
            continue
        text = git_show(base, src)
        a, b = split_body(text, heading)
        body = text[a:b]
        # (1) the body is in the destination byte for byte, under its heading
        if heading + "\n" + body not in dest:
            problems.append(f"{dst}: the body of {heading!r} is not there byte for byte")
        # (2) the source keeps the heading and the pointer, and the body is gone
        if heading + "\n" + pointer(anchor) not in cur:
            problems.append(f"{src}: heading {heading!r} lost its pointer")
        if len(body.strip()) > 200 and body.strip() in cur:
            problems.append(f"{src}: the body of {heading!r} is still there")
        restored.setdefault(src, [text, cur])
    # (3) putting every body back gives the base source exactly
    for src, (text, cur) in restored.items():
        back = cur
        for s, _, heading, anchor in MOVES:
            if s != src:
                continue
            a, b = split_body(text, heading)
            back = back.replace(heading + "\n" + pointer(anchor), heading + "\n" + text[a:b], 1)
        if back != text:
            problems.append(f"{src}: the bodies put back do not give the source of {base} "
                            "(expected only if another branch changed the source since)")
    return problems


def check_tree() -> list:
    """!
    @brief Verify the moves without a base commit: every pointer of the source leads to a heading of the destination.

    @return list Problems found.
    """
    problems = []
    for src, dst, heading, anchor in MOVES:
        cur = (ROOT / src).read_text(encoding="utf-8")
        dest = (ROOT / dst).read_text(encoding="utf-8")
        if heading + "\n" + pointer(anchor) not in cur:
            problems.append(f"{src}: heading {heading!r} lost its pointer")
        if "\n" + heading + "\n" not in dest:
            problems.append(f"{dst}: heading {heading!r} missing")
    return problems


def numbers_kept(base: str, rel: str, dests: list) -> list:
    """!
    @brief For a rewrite that is not byte for byte: every precise number that left a document must be in a destination.

    @details A precise number is one with two decimals or more, or a signed percentage (the numbers a reader quotes).
    The later simplification branches (theory, models, guide) use this check with the documents that receive the
    numbers, usually `docs/validation.md` and `docs/validation-history.md`.

    @param base   The commit before the rewrite.
    @param rel    The rewritten document.
    @param dests  The documents that must hold the numbers that left it.
    @return list The numbers that left `rel` and are in none of `dests`.
    """
    num = re.compile(r"[-+−]?\d+\.\d{2,}|[-+−]\d+(?:\.\d+)? ?%")
    before = set(num.findall(git_show(base, rel)))
    after = set(num.findall((ROOT / rel).read_text(encoding="utf-8")))
    held = set()
    for d in dests:
        held |= set(num.findall((ROOT / d).read_text(encoding="utf-8")))
    return [f"{rel}: number {n!r} left and is in none of {dests}" for n in sorted(before - after - held)]


def main() -> int:
    """!
    @brief Command line entry point.

    @return int 0 when nothing was lost, 1 otherwise.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    ap.add_argument("--base", help="commit of the sources before the moves")
    ap.add_argument("--apply", action="store_true", help="perform the moves (once)")
    ap.add_argument("--numbers-kept", nargs="+", metavar="FILE",
                    help="with --base: the rewritten document followed by the documents that must hold its numbers")
    args = ap.parse_args()
    if args.numbers_kept:
        if not args.base or len(args.numbers_kept) < 2:
            sys.exit("--numbers-kept needs --base, the rewritten document and at least one destination")
        problems = numbers_kept(args.base, args.numbers_kept[0], args.numbers_kept[1:])
        for p in problems:
            print("LOST:", p)
        print(f"numbers of {args.numbers_kept[0]}: {'OK' if not problems else 'FAILED'}")
        return 1 if problems else 0
    if args.apply:
        if not args.base:
            sys.exit("--apply needs --base")
        apply(args.base)
    problems = check_tree() + (check(args.base) if args.base else [])
    for p in problems:
        print("LOST:", p)
    n = len(MOVES)
    print(f"{n} moves checked{' against ' + args.base if args.base else ''}: {'OK' if not problems else 'FAILED'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
