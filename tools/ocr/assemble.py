#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file assemble.py
@brief Deterministic assembly of the per-page OCR outputs of one PDF into one Markdown file (`papers/md-final/<stem>.md`).

@details The same inputs always give the same file. Steps: choose the text of each page (Claude, else Gemini, else a
`[missing]` note); remove running headers, footers and lone page numbers (lines that repeat on at least three pages at the
top or bottom, compared without digits); join a word hyphenated across a page break and a sentence cut by a page break;
keep a marker `<!-- page N | printed M -->` before each page; build the YAML header (citation from `notes/INDEX.md`,
page counts, the provider of every page, the files of the repository that cite the paper) and a table of contents from
the headings. Nothing is invented: a page without a text is marked `[missing]`, a header field that is not known is
`unknown`. Equations are kept as the provider wrote them (the paper's own numbering is not rebuilt), and the section
"Equations used by the program" is not generated (it needs a reader who checks the theory against the page).
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

HEADER_ZONE = 2        # non-empty lines at the top and bottom of a page that may be running text
MIN_REPEAT = 3         # a header or footer must repeat on this many pages
PAGE_RE = re.compile(r"^\s*<!--\s*page\s+\d+\s*-->\s*", re.I)
NUM_ONLY = re.compile(r"^\s*(page\s+)?\d{1,4}\s*$", re.I)


def strip_marker(text: str) -> str:
    """!
    @brief Remove the leading `<!-- page N -->` marker of a per-page output.
    @param text Page text.
    @return str Text without the marker.
    """
    return PAGE_RE.sub("", text, count=1)


def norm_line(line: str) -> str:
    """!
    @brief Normal form of a line for the header/footer comparison (digits and spacing removed, lower case).
    @param line A text line.
    @return str Normalised text.
    """
    return re.sub(r"[\d\s*_#|]+", " ", line).strip().lower()


def find_running_lines(pages: dict[int, str]) -> set[str]:
    """!
    @brief Lines that repeat at the top or bottom of at least three pages (running titles, journal lines, watermarks).
    @param pages Mapping PDF page -> text.
    @return set[str] Normalised lines to drop at the edges.
    """
    count: collections.Counter = collections.Counter()
    for text in pages.values():
        lines = [x for x in text.splitlines() if x.strip()]
        edge = lines[:HEADER_ZONE] + lines[-HEADER_ZONE:]
        for n in {norm_line(x) for x in edge if len(norm_line(x)) >= 6}:
            count[n] += 1
    return {n for n, c in count.items() if c >= MIN_REPEAT}


def clean_page(text: str, running: set[str]) -> str:
    """!
    @brief Remove running lines at the page edges and lone page numbers.
    @param text    Page text.
    @param running Normalised running lines from `find_running_lines`.
    @return str Cleaned text.
    """
    lines = text.splitlines()
    idx = [i for i, x in enumerate(lines) if x.strip()]
    drop = set()
    for i in idx[:HEADER_ZONE] + idx[-HEADER_ZONE:]:
        if NUM_ONLY.match(lines[i]) or norm_line(lines[i]) in running:
            drop.add(i)
    return "\n".join(x for i, x in enumerate(lines) if i not in drop).strip()


def join_pages(chunks: list[tuple[str, str]]) -> str:
    """!
    @brief Concatenate pages with their markers, joining a word or sentence cut by the page break.
    @param chunks List of (marker, cleaned text) in page order.
    @return str Body text.
    """
    out: list[str] = []
    for marker, text in chunks:
        if out and text and out[-1]:
            prev = out[-1].rstrip()
            last = prev.splitlines()[-1] if prev else ""
            first = text.lstrip().splitlines()[0] if text.strip() else ""
            plain = not last.lstrip().startswith(("#", "|", "$$", "<!--", "[figure", "**Figure", "**Table"))
            if plain and last.endswith("-") and not last.endswith("--") and first[:1].islower():
                # hyphenated word: glue the halves and put the marker after the first word of the new page
                word, _, rest = text.lstrip().partition(" ")
                out[-1] = prev[:-1] + word
                out.append(marker)
                out.append(rest.lstrip())
                continue
            if plain and last and last[-1] not in ".:;?!)]$|" and first[:1].islower():
                # sentence cut by the break: the marker is placed on its own line, the paragraph continues after it
                out.append(marker)
                out.append(text.lstrip())
                out.append("\x00JOIN")
                continue
        out.append(marker)
        out.append(text)
    body = "\n\n".join(out)
    # a paragraph that continues across a marker is rejoined with a single newline instead of a blank line
    return body.replace("\n\n\x00JOIN", "")


def index_row(papers: Path, stem: str) -> dict:
    """!
    @brief The row of `notes/INDEX.md` for a PDF.
    @param papers Papers folder.
    @param stem   File stem.
    @return dict Keys `key`, `citation`, `supports` (empty strings when the row is missing).
    """
    path = papers / "notes" / "INDEX.md"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[0] == stem + ".pdf":
                return {"key": cells[1], "citation": cells[2], "supports": cells[3]}
    return {"key": "", "citation": "", "supports": ""}


def used_by(root: Path, stem: str, key: str) -> list[str]:
    """!
    @brief Repository files that cite the paper by its stem or bibliography key.
    @param root Repository root (main checkout).
    @param stem File stem.
    @param key  Bibliography key (may be empty or in parentheses).
    @return list[str] Sorted relative paths (theory, bibliography, research READMEs, program modules).
    """
    needles = [stem] + ([key.strip("()")] if key.strip("()") and len(key.strip("()")) > 5 else [])
    files = [root / "docs" / "theory.md", root / "docs" / "models.md", root / "docs" / "validation.md",
             root / "research" / "theory" / "BIBLIOGRAPHY.md"]
    files += sorted((root / "research").glob("*/README.md")) + sorted((root / "pcbthermal").glob("*.py"))
    hits = []
    for f in files:
        if f.is_file():
            t = f.read_text(encoding="utf-8", errors="ignore")
            if any(n in t for n in needles):
                hits.append(str(f.relative_to(root)))
    return sorted(set(hits))


def ranges(pages: list[int]) -> str:
    """!
    @brief Compact text of a page list, `1-3,5`.
    @param pages Sorted page numbers.
    @return str The ranges.
    """
    out, i = [], 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


def yaml_text(s: str) -> str:
    """!
    @brief Quote a string for YAML.
    @param s Text.
    @return str Double-quoted text.
    """
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def toc(body: str) -> str:
    """!
    @brief Table of contents from the Markdown headings.
    @param body Body text.
    @return str A bullet list (empty text when there are no headings).
    """
    items = []
    for m in re.finditer(r"^(#{1,4})\s+(.+?)\s*$", body, re.M):
        title = m.group(2).strip("* ")
        items.append("  " * (len(m.group(1)) - 1) + f"- {title}")
    return "\n".join(items)


def assemble(papers: Path, stem: str, root: Path, page_count: int, pdf_pages_text: dict[int, str] | None = None,
             printed: dict[int, int | None] | None = None, born_digital: bool | None = None) -> str:
    """!
    @brief Build the final Markdown of one PDF.
    @param papers         Papers folder (reads `ocr/anthropic/<stem>_p<N>.md`, `ocr/<stem>_p<N>.md`, `notes/INDEX.md`).
    @param stem           File stem.
    @param root           Repository root for the used-by search.
    @param page_count     Number of PDF pages.
    @param pdf_pages_text Unused placeholder for a text layer (kept for callers that want to extend the check).
    @param printed        Mapping PDF page -> printed page number (None when unknown).
    @param born_digital   True for a PDF with a text layer, False for a scan, None when unknown.
    @return str The file content.
    """
    printed = printed or {}
    ocr = papers / "ocr"
    src: dict[int, str] = {}
    prov: dict[int, str] = {}
    for p in range(1, page_count + 1):
        for name, f in (("claude", ocr / "anthropic" / f"{stem}_p{p}.md"), ("gemini", ocr / f"{stem}_p{p}.md")):
            if f.is_file():
                src[p] = strip_marker(f.read_text(encoding="utf-8"))
                prov[p] = name
                break
    running = find_running_lines(src)
    chunks = []
    for p in range(1, page_count + 1):
        pr = printed.get(p)
        marker = f"<!-- page {p} | printed {pr if pr else '?'} -->"
        text = clean_page(src[p], running) if p in src else "[missing]"
        chunks.append((marker, text))
    body = join_pages(chunks)
    row = index_row(papers, stem)
    pr_nums = [v for v in printed.values() if v]
    by = {n: ranges([p for p, v in prov.items() if v == n]) for n in ("claude", "gemini")}
    missing = [p for p in range(1, page_count + 1) if p not in src]
    head = [
        "---",
        f"title: {yaml_text(row['citation'] or stem)}",
        "citation_source: notes/INDEX.md" if row["citation"] else "citation_source: unknown",
        f"source_pdf: {stem}.pdf",
        f"pdf_pages: {page_count}",
        f"printed_pages: {yaml_text(f'{min(pr_nums)}-{max(pr_nums)}' if pr_nums else 'unknown')}",
        f"pdf_type: {'born-digital' if born_digital else 'scan' if born_digital is False else 'unknown'}",
        f"bibliography_key: {yaml_text(row['key'] or 'unknown')}",
        f"supports: {yaml_text(row['supports'] or 'unknown')}",
        f"provider_pages: {{claude: {yaml_text(by['claude'])}, gemini: {yaml_text(by['gemini'])}, "
        f"missing: {yaml_text(ranges(missing))}}}",
        "licence: open copy kept locally, not redistributed; third-party material, never committed",
        "reading_status: machine   # becomes verified only when the reviewer compares the page images",
        "used_by:",
    ]
    head += [f"  - {u}" for u in used_by(root, stem, row["key"])] or ["  - none found"]
    head.append("---")
    toc_text = toc(body)
    return "\n".join(head) + "\n\n# Contents\n\n" + (toc_text or "(no headings found)") + "\n\n---\n\n" + body + "\n"
