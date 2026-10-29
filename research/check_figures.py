"""!
@file check_figures.py
@brief Checks the figures of every research folder against the figure rules of `CLAUDE.md` ("Research branches": "Diagrams and illustrations (always)" and "Figures").
@details Question answered: is every figure of every `research/<topic>/figures/` linked from a document of its folder, does every image link resolve, is each figure captioned, is each number `fig_NN` used once, and does the folder have at least one data figure and one diagram?
         The conventions: figures live in `research/<topic>/figures/` as `fig_NN_topic.png` (NN in order of creation, one numbering for the data figures of `scripts/make_figures.py` and the diagrams of `scripts/make_diagrams.py`, shapes shared in `research/diagram_kit.py`), are committed on purpose, and are linked from the README files with `![caption](figures/fig_NN_topic.png)` followed by an italic line with the figure number and file name.
         The checks, for every folder that has a `figures/` directory:
           1. every PNG in `figures/` is linked, with the Markdown image syntax `![...](path)`, from a `.md` file of the folder;
           2. every image link in the `.md` files of the folder resolves to an existing file (the path is relative to the `.md` file, so `docs/` files use `../figures/`);
           3. no figure number NN is used by two different files;
           4. the folder has at least one data figure (its name or number appears in `scripts/make_figures.py`) and at least one diagram (in `scripts/make_diagrams.py`);
           5. every figure has a caption line (an italic line that contains the file name) within a few lines after one of its links.
         Freshness by file time is not checked (it is not reliable after a checkout). Nothing is drawn or regenerated here.
         Run from the repository root: `.venv/bin/python research/check_figures.py [folder ...]` (no argument = every folder). Exit code 0 when all checks pass, 1 with the list of failures otherwise.
"""

import re
import sys
from pathlib import Path

## Directory that holds the research folders (the folder of this file).
ROOT = Path(__file__).resolve().parent
## Markdown image syntax: ![alt](target); the target ends at the first space or closing parenthesis.
IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
## A figure file name with its number.
FIGURE_NAME = re.compile(r"fig_(\d+)_[A-Za-z0-9_]+\.png")
## How many lines after an image link a caption line may start.
CAPTION_WINDOW = 6
## Directories inside a folder whose .md files are not documents (data and outputs are git-ignored).
SKIP_DIRS = {"data", "out", "__pycache__"}


def markdown_files(folder: Path) -> list:
    """!
    @brief List the Markdown documents of a research folder, skipping the git-ignored data and output directories.
    @param folder Research folder.
    @return list Sorted paths of the `.md` files.
    """
    # rglob walks every sub-folder; filter by the path parts relative to the folder
    return sorted(p for p in folder.rglob("*.md")
                  if not (set(p.relative_to(folder).parts) & SKIP_DIRS))


def find_links(md: Path) -> list:
    """!
    @brief Find the local image links of a Markdown file.
    @param md Markdown file.
    @return list Tuples (line number starting at 1, link target) for the links that are not URLs.
    """
    links = []
    for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
        for target in IMAGE_LINK.findall(line):
            # Web images are outside the repository: nothing to resolve
            if not target.startswith(("http://", "https://", "data:")):
                links.append((number, target))
    return links


def has_caption(md: Path, line_no: int, name: str) -> bool:
    """!
    @brief Tell whether an italic caption line naming the figure follows an image link.
    @param md Markdown file that holds the link.
    @param line_no Line number (from 1) of the image link.
    @param name File name of the figure, for example `fig_03_x.png`.
    @return bool True when one of the next lines is an italic line (starts with a single `*`, ends with `*`) that contains the file name.
    """
    lines = md.read_text(encoding="utf-8").splitlines()
    # The window starts at the link line itself: a caption may follow on the same paragraph
    for text in lines[line_no: line_no + CAPTION_WINDOW]:
        s = text.strip()
        if s.startswith("*") and not s.startswith("**") and s.endswith("*") and name in s:
            return True
    return False


def script_mentions(script: Path, name: str) -> bool:
    """!
    @brief Tell whether a figure script produces a figure, by grepping it for the file name or the figure number.
    @param script Path of `make_figures.py` or `make_diagrams.py` (may not exist).
    @param name File name of the figure, for example `fig_03_x.png`.
    @return bool True when the script text contains the full file name, or the prefix `fig_NN` (scripts that build the path from a variable) or an f-string `fig_{...}`.
    """
    if not script.exists():
        return False
    text = script.read_text(encoding="utf-8")
    prefix = name.split("_")[0] + "_" + name.split("_")[1]
    # A save call with the literal name is the strong evidence; the prefix covers names built in a variable
    return name in text or prefix + "_" in text or "fig_{" in text


def check_folder(folder: Path) -> tuple:
    """!
    @brief Run all the checks on one research folder.
    @param folder Research folder that has a `figures/` directory.
    @return tuple (list of failure messages, list of messages that need a figure drawn).
    """
    failures, to_draw = [], []
    figures = sorted((folder / "figures").glob("*.png"))
    mds = markdown_files(folder)
    # Link table: resolved path -> list of (md file, line number)
    linked = {}
    for md in mds:
        for line_no, target in find_links(md):
            path = (md.parent / target.split("#")[0]).resolve()
            if not path.exists():
                failures.append(f"{md.relative_to(ROOT)}:{line_no}: broken image link {target}")
            linked.setdefault(path, []).append((md, line_no))
    numbers = {}
    for fig in figures:
        match = FIGURE_NAME.fullmatch(fig.name)
        if not match:
            failures.append(f"{fig.relative_to(ROOT)}: name does not follow fig_NN_topic.png")
            continue
        numbers.setdefault(match.group(1), []).append(fig.name)
        links = linked.get(fig.resolve(), [])
        if not links:
            failures.append(f"{fig.relative_to(ROOT)}: not linked from any .md file of the folder")
        elif not any(has_caption(md, ln, fig.name) for md, ln in links):
            failures.append(f"{fig.relative_to(ROOT)}: no italic caption line with the file name after its link")
    for number, names in sorted(numbers.items()):
        if len(names) > 1:
            failures.append(f"{folder.name}/figures: number {number} used by {', '.join(names)}")
    data = [f for f in figures if script_mentions(folder / "scripts" / "make_figures.py", f.name)]
    diagrams = [f for f in figures if script_mentions(folder / "scripts" / "make_diagrams.py", f.name)]
    if not data:
        to_draw.append(f"{folder.name}: no data figure (make_figures.py missing or names none of the figures)")
    if not diagrams:
        to_draw.append(f"{folder.name}: no diagram (make_diagrams.py missing or names none of the figures)")
    return failures, to_draw


def main(argv: list) -> int:
    """!
    @brief Check the folders named on the command line, or all of them, and print the failures.
    @param argv Folder names under `research/` (empty = every folder with a `figures/` directory).
    @return int Exit code: 0 when everything passes, 1 otherwise.
    """
    names = argv or sorted(p.parent.name for p in ROOT.glob("*/figures"))
    all_failures = []
    for name in names:
        failures, to_draw = check_folder(ROOT / name)
        all_failures += failures + to_draw
        print(f"{name:26s} {'ok' if not failures + to_draw else str(len(failures + to_draw)) + ' problem(s)'}")
    for message in all_failures:
        print("FAIL", message)
    return 1 if all_failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
