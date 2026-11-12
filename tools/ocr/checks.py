#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file checks.py
@brief Offline quality checks of the OCR library: first-line check, equation-structure check and integrity audit.

@details No provider, key or network is used; everything reads `papers/`.
* `firstline`: a typical Claude error is a sentence invented at the top of a page (it is not on the page). On a
  born-digital PDF the first text line of the machine page must be found among the first lines of the PDF text layer of
  the same page (normalised token overlap). Scans, garbage text layers and pages that start with a formula or a figure
  are reported as not checkable, never as passed.
* `eqcheck`: counts `$..$` / `$$..$$` spans and `\\tag{n}` equation numbers of a page and compares them with the formula
  density and the equation numbers of the text layer and with the other provider's page when both exist.
* `audit`: integrity of the assembled library (`md-final`): header fields, page markers, `[missing]` pages that exist
  in a provider, reading status against `ocr/reading_status.json`, corrected pages in place of provider pages, key-like
  text, confidential files, orphan files.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from pathlib import Path

from tools.ocr import config, keys, status as st, suspects
from tools.ocr.papermap import MATH_CHARS, formula_score

FIRST_LINES_IN_LAYER = 12      # the first line of a page must be among this many text-layer lines
MIN_OVERLAP = 0.6              # share of the machine line's tokens found in those layer lines
MIN_LAYER_WORDS = 25           # a text layer with fewer words is not a basis (figure page, scan with a stray stamp)
MIN_TOKENS = 3                 # a first line with fewer tokens is combined with the next one, else not checkable
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
MATH_SPAN_RE = re.compile(r"\$\$.+?\$\$|\$[^$\n]+\$", re.S)
TAG_RE = re.compile(r"\\tag\*?\{\s*\(?([^}()]+?)\)?\s*\}")
FIGURE_LINE_RE = re.compile(r"^(\*\*)?(!?\[(figure|image|plot|diagram)\b)", re.I)
NOTE_RE = re.compile(r"\*\([^)]*\)\*")       # the provider's own note, e.g. `*(header, right: Summary)*`
# a number written at the end of a display equation instead of \tag{n}: `\qquad (1)`, `\quad\text{(2)}`, `\hfill (3)`
TRAIL_NUM_RE = re.compile(r"\\(?:q?quad|hfill|;|,)\s*(?:\\text\{)?\(\s*(\d{1,3}(?:\.\d+)?[a-z]?)\s*\)\}?\s*(?:\\\\)?\s*(?:\$\$|\\end\{)")
PAGE_FILE_RE = re.compile(r"^(?P<stem>.+)_p(?P<page>\d+)\.md$")

# provider label -> folder relative to papers/ocr (Gemini pages sit directly in papers/ocr)
SOURCE_DIRS = {"claude": "anthropic", "claude-whole": "anthropic/whole", "retry": "retry", "corrected": "corrected",
               "openrouter": "openrouter", "gemini": ""}
DEFAULT_SOURCES = ("claude", "claude-whole", "retry", "corrected")


# ---------------------------------------------------------------- shared helpers

def page_files(papers: Path, sources=DEFAULT_SOURCES, stems: set[str] | None = None,
               pages: set[int] | None = None) -> list[tuple[str, str, int, Path]]:
    """!
    @brief The per-page Markdown files of the chosen sources.
    @param papers  Papers folder.
    @param sources Labels from `SOURCE_DIRS`.
    @param stems   Keep only these PDF stems (None: all).
    @param pages   Keep only these PDF pages (None: all).
    @return list[tuple] (source label, stem, page, path), sorted by stem, page and source.
    """
    out = []
    for label in sources:
        folder = papers / "ocr" / SOURCE_DIRS[label]
        if not folder.is_dir():
            continue
        for f in folder.glob("*_p*.md"):
            m = PAGE_FILE_RE.match(f.name)
            if not m or not f.is_file():
                continue
            stem, page = m.group("stem"), int(m.group("page"))
            if (stems and stem not in stems) or (pages and page not in pages):
                continue
            out.append((label, stem, page, f))
    return sorted(out, key=lambda x: (x[1], x[2], x[0]))


def norm_tokens(text: str) -> list[str]:
    """!
    @brief Tokens for the text comparison: NFKC (ligatures expanded), lower case, letters and numbers of 2+ characters.
    @param text Any text (math spans and comments should be removed by the caller).
    @return list[str] The tokens in order.
    """
    t = unicodedata.normalize("NFKC", text).lower().replace("\u00ad", "")
    return re.findall(r"[^\W_]{2,}", t)


def squeeze(text: str) -> str:
    """!
    @brief Letters and digits of a text, lower case, without spaces (NFKC), for a match across broken words.
    @param text Any text.
    @return str The squeezed text.
    """
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).lower().replace("\u00ad", ""))


def first_text_lines(md: str, count: int = 2) -> list[str]:
    """!
    @brief The first non-empty lines of a machine page, without the page marker and the comments.
    @param md    Page Markdown.
    @param count How many lines.
    @return list[str] The raw lines.
    """
    body = COMMENT_RE.sub("", md)
    # a figure description is the provider's own words (the prompt asks for it), so it cannot be compared with the layer
    lines = [x.strip() for x in body.splitlines() if x.strip() and not FIGURE_LINE_RE.match(x.strip())]
    return lines[:count]


def line_tokens(line: str) -> list[str]:
    """!
    @brief Tokens of a Markdown line that can be compared with a text layer: prose only, math and markup removed.
    @param line A line of the machine page.
    @return list[str] The tokens (empty for a formula, a figure note or a table rule).
    """
    if line.startswith(("[figure", "[Figure", "|---", "| ---")):
        return []
    text = NOTE_RE.sub(" ", MATH_SPAN_RE.sub(" ", line))
    text = re.sub(r"[#*>|_`]", " ", text)
    return norm_tokens(text)


def layer_usable(layer: str) -> str | None:
    """!
    @brief Why a PDF text layer cannot be a basis, or None when it can.
    @param layer Text layer of one page.
    @return str|None "scan or empty layer", "garbage text layer" or None.
    """
    if len(re.findall(r"\w+", layer)) < MIN_LAYER_WORDS:
        return "scan or empty layer"
    if suspects.garbage_text_layer(layer):
        return "garbage text layer"
    return None


def check_first_line(md: str, layer: str, n_lines: int = FIRST_LINES_IN_LAYER, threshold: float = MIN_OVERLAP) -> dict:
    """!
    @brief Compare the first text line of a machine page with the PDF text layer of the same page.
    @param md        Machine page (Markdown).
    @param layer     Text layer of the page ("" for a scan).
    @param n_lines   Number of text-layer lines in which the first line must be found.
    @param threshold Minimum share of the line's tokens found there.
    @return dict `verdict` (`ok`, `moved` = found elsewhere on the page, `FLAG`, `not checkable`), `reason`, `line`
            (the first line, shortened), `overlap` (in the first layer lines) and `overlap_page` (anywhere in the layer).
    """
    why = layer_usable(layer)
    lines = first_text_lines(md, 2)
    if why:
        return {"verdict": "not checkable", "reason": why, "line": (lines[0] if lines else "")[:100], "overlap": None, "overlap_page": None}
    if not lines:
        return {"verdict": "not checkable", "reason": "empty page or only a figure description", "line": "", "overlap": None, "overlap_page": None}
    toks = line_tokens(lines[0])
    shown = lines[0]
    if len(toks) < MIN_TOKENS and len(lines) > 1:
        # a heading number or a one-word title says too little: use the next line as well
        toks += line_tokens(lines[1])
        shown = lines[0] + " / " + lines[1]
    if len(toks) < MIN_TOKENS:
        return {"verdict": "not checkable", "reason": "first line is a formula, a figure or too short", "line": shown[:100],
                "overlap": None, "overlap_page": None}
    layer_lines = [x for x in layer.splitlines() if x.strip()]
    head_text, whole_text = " ".join(layer_lines[:n_lines]), layer
    head, whole = set(norm_tokens(head_text)), set(norm_tokens(whole_text))
    # old PDFs break words into fragments ("prop er", "b e") or glue footnote marks to names ("NAME1"): a token of four
    # or more characters also counts as found when it is a substring of the layer squeezed without spaces
    head_sq, whole_sq = squeeze(head_text), squeeze(whole_text)
    o_head = sum(t in head or (len(t) >= 4 and t in head_sq) for t in toks) / len(toks)
    o_page = sum(t in whole or (len(t) >= 4 and t in whole_sq) for t in toks) / len(toks)
    if o_head >= threshold:
        verdict = "ok"
    elif o_page >= 0.8:
        verdict = "moved"
    else:
        verdict = "FLAG"
    return {"verdict": verdict, "reason": "", "line": shown[:100], "overlap": round(o_head, 2), "overlap_page": round(o_page, 2)}


def pdf_layers(pdf: Path) -> dict[int, str]:
    """!
    @brief Text layer of every page of a PDF.
    @param pdf PDF path.
    @return dict[int, str] Page (1-based) to text; empty when pypdfium2 is missing or the file cannot be opened.
    """
    try:
        from . import render
        return {i + 1: t for i, t in enumerate(render.page_texts(pdf))}
    except Exception:
        return {}


def md_cell(text: str, limit: int = 100) -> str:
    """!
    @brief Make untrusted page text safe for a Markdown table cell.
    @param text Text from a page.
    @param limit Maximum length.
    @return str One line without pipes, backticks or line breaks.
    """
    return re.sub(r"[|`\r\n]", " ", text)[:limit].strip()


def run_firstline(papers: Path, stems: set[str] | None = None, pages: set[int] | None = None, sources=DEFAULT_SOURCES,
                  n_lines: int = FIRST_LINES_IN_LAYER, threshold: float = MIN_OVERLAP, layers=None) -> dict:
    """!
    @brief Run the first-line check on the pages that exist.
    @param papers    Papers folder.
    @param stems     Stems to check (None: all that have a page file).
    @param pages     Pages to check (None: all).
    @param sources   Page sources, labels of `SOURCE_DIRS`.
    @param n_lines   Layer lines searched.
    @param threshold Token overlap threshold.
    @param layers    Function PDF path -> {page: text} (default `pdf_layers`, looked up at call time; replaced in tests).
    @return dict `rows` (one per page file: source, stem, page, result of `check_first_line`) and `counts` per verdict.
    """
    layers = layers or pdf_layers
    files = page_files(papers, sources, stems, pages)
    by_stem: dict[str, list] = collections.defaultdict(list)
    for item in files:
        by_stem[item[1]].append(item)
    rows = []
    for stem, items in sorted(by_stem.items()):
        pdf = papers / "pdf" / f"{stem}.pdf"
        text = layers(pdf) if pdf.is_file() else {}
        for label, _, page, path in items:
            res = check_first_line(path.read_text(encoding="utf-8", errors="replace"), text.get(page, ""), n_lines, threshold)
            if not pdf.is_file():
                res.update(verdict="not checkable", reason="no PDF in papers/pdf")
            rows.append({"source": label, "stem": stem, "page": page, **res})
    counts = collections.Counter(r["verdict"] for r in rows)
    return {"rows": rows, "counts": dict(counts)}


def render_firstline(result: dict) -> str:
    """!
    @brief The Markdown report of `run_firstline` (deterministic: no dates).
    @param result Output of `run_firstline`.
    @return str The report text.
    """
    rows, counts = result["rows"], result["counts"]
    out = ["# First-line check", "",
           "Generated by `python -m tools.ocr firstline`. The first text line of each machine page is compared with the first "
           f"{FIRST_LINES_IN_LAYER} lines of the PDF text layer of the same page (normalised tokens, ligatures expanded, overlap "
           f"at least {MIN_OVERLAP}). Only born-digital pages with a usable text layer are checkable. **A flag is not an error: "
           "the reviewer compares the flagged page with its image.** `moved` = the line is on the page but not at the top "
           "(reading order of a two-column layer or a figure caption).", "",
           f"Pages: {len(rows)}. " + ", ".join(f"{k}: {counts[k]}" for k in sorted(counts)), "",
           "## By source", "", "| source | pages | ok | moved | FLAG | not checkable |", "| :-- | --: | --: | --: | --: | --: |"]
    for s in sorted({r["source"] for r in rows}):
        sel = [r for r in rows if r["source"] == s]
        c = collections.Counter(r["verdict"] for r in sel)
        out.append(f"| {s} | {len(sel)} | {c['ok']} | {c['moved']} | {c['FLAG']} | {c['not checkable']} |")
    why = collections.Counter(r["reason"] for r in rows if r["verdict"] == "not checkable")
    out += ["", "## Not checkable, by reason", "", "| reason | pages |", "| :-- | --: |"]
    out += [f"| {md_cell(k)} | {v} |" for k, v in sorted(why.items())]
    for title, verdict in (("Flagged pages (first line not found in the text layer)", "FLAG"), ("Moved (found lower on the page)", "moved")):
        sel = sorted((r for r in rows if r["verdict"] == verdict), key=lambda r: (r["overlap"], r["stem"], r["page"]))
        out += ["", f"## {title}", ""]
        if not sel:
            out.append("None.")
            continue
        out += ["| stem | page | source | overlap (top / page) | first line of the machine page |", "| :-- | --: | :-- | :-- | :-- |"]
        out += [f"| {r['stem']} | {r['page']} | {r['source']} | {r['overlap']} / {r['overlap_page']} | {md_cell(r['line'])} |" for r in sel]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- equation structure

def md_eq_stats(md: str) -> dict:
    """!
    @brief Equation structure of a machine page.
    @param md Page Markdown.
    @return dict `display` (count of `$$..$$`), `inline` (count of `$..$`), `tags` (set of `\\tag{n}` numbers).
    """
    body = COMMENT_RE.sub("", md)
    display = re.findall(r"\$\$.+?\$\$", body, flags=re.S)
    rest = re.sub(r"\$\$.+?\$\$", " ", body, flags=re.S)
    tags = {t.strip() for t in TAG_RE.findall(body)} | {m for d in display for m in TRAIL_NUM_RE.findall(d)}
    return {"display": len(display), "inline": len(re.findall(r"\$[^$\n]+\$", rest)), "tags": tags}


def layer_eq_numbers(layer: str) -> set[str]:
    """!
    @brief Equation numbers visible in a text layer: a line that is only `(n)`, or a line with `=` that ends in `(n)`.
    @param layer Text layer of a page.
    @return set[str] Numbers such as `22` or `3a`.
    """
    found = set()
    for line in layer.splitlines():
        line = line.strip()
        m = re.fullmatch(r"\(?(\d{1,3}[a-z]?)\)", line)
        if m:
            found.add(m.group(1))
            continue
        m = re.search(r"=.*\((\d{1,3}[a-z]?)\)\s*$", line)
        if m:
            found.add(m.group(1))
    return found


def check_equations(md: str, layer: str = "", other_md: str | None = None) -> list[str]:
    """!
    @brief Mismatches between the equation structure of a machine page and the references available.
    @param md       Machine page.
    @param layer    Text layer of the page ("" or unusable: the layer checks are skipped).
    @param other_md The other provider's page, or None.
    @return list[str] Short mismatch descriptions (empty when nothing disagrees).
    """
    s = md_eq_stats(md)
    out = []
    if not layer_usable(layer):
        score, _ = formula_score(layer)
        if score >= 0.08 and s["display"] + s["inline"] == 0:
            out.append(f"text layer is formula heavy (score {score:.2f}) but the page has no $ spans")
        if s["display"] >= 3 and score < 0.02:
            out.append(f"(weak) {s['display']} display equations but the text layer has almost no formula glyphs (score {score:.2f}; equations may be images)")
        nums = layer_eq_numbers(layer)
        if nums or s["tags"]:
            missing, extra = sorted(nums - s["tags"]), sorted(s["tags"] - nums)
            if missing:
                out.append("equation numbers in the text layer without a \\tag: " + ",".join(missing[:8]))
            if extra:
                out.append("\\tag numbers not in the text layer: " + ",".join(extra[:8]))
    if other_md is not None:
        o = md_eq_stats(other_md)
        if abs(s["display"] - o["display"]) > max(1, round(0.34 * max(s["display"], o["display"]))):
            out.append(f"display equations {s['display']} here, {o['display']} in the other provider")
        # Gemini often leaves the numbers out of the LaTeX, so a page with no numbers on one side says nothing
        if s["tags"] and o["tags"] and s["tags"] != o["tags"]:
            out.append("\\tag numbers differ from the other provider: " + ",".join(sorted(s["tags"] ^ o["tags"])[:8]))
    return out


def run_eqcheck(papers: Path, stems: set[str] | None = None, pages: set[int] | None = None, sources=("claude", "claude-whole", "retry", "corrected"),
                layers=None) -> dict:
    """!
    @brief Run the equation-structure check.
    @param papers  Papers folder.
    @param stems   Stems to check (None: all).
    @param pages   Pages to check (None: all).
    @param sources Page sources.
    @param layers  Function PDF path -> {page: text} (default `pdf_layers`).
    @return dict `rows` (source, stem, page, `issues`, `display`, `tags`, `other` = compared with Gemini) and `checked`.
    """
    layers = layers or pdf_layers
    files = page_files(papers, sources, stems, pages)
    by_stem: dict[str, list] = collections.defaultdict(list)
    for item in files:
        by_stem[item[1]].append(item)
    rows = []
    for stem, items in sorted(by_stem.items()):
        pdf = papers / "pdf" / f"{stem}.pdf"
        text = layers(pdf) if pdf.is_file() else {}
        for label, _, page, path in items:
            md = path.read_text(encoding="utf-8", errors="replace")
            g = papers / "ocr" / f"{stem}_p{page}.md"
            other = g.read_text(encoding="utf-8", errors="replace") if label != "gemini" and g.is_file() else None
            s = md_eq_stats(md)
            rows.append({"source": label, "stem": stem, "page": page, "display": s["display"], "inline": s["inline"],
                         "tags": sorted(s["tags"]), "other": other is not None,
                         "issues": check_equations(md, text.get(page, ""), other)})
    return {"rows": rows, "checked": len(rows)}


def render_eqcheck(result: dict) -> str:
    """!
    @brief The Markdown report of `run_eqcheck`.
    @param result Output of `run_eqcheck`.
    @return str The report text.
    """
    rows = result["rows"]
    bad = [r for r in rows if r["issues"]]
    out = ["# Equation-structure check", "",
           "Generated by `python -m tools.ocr eqcheck`. For each machine page: the number of `$$..$$` and `$..$` spans and the "
           "`\\tag{n}` numbers, against the formula density and the equation numbers of the PDF text layer (born-digital pages "
           "with a usable layer) and against the Gemini page when both exist. A mismatch is a place to look, not an error.", "",
           f"Pages: {len(rows)}; with a mismatch: {len(bad)} ({sum(any(not i.startswith('(weak)') for i in r['issues']) for r in bad)} with a strong one; "
           f"`(weak)` = equations drawn as images or glyph-encoded, which says little); compared with a Gemini page: {sum(r['other'] for r in rows)}.", "",
           "## Mismatches", ""]
    if not bad:
        out.append("None.")
    else:
        out += ["| stem | page | source | display | tags | mismatch |", "| :-- | --: | :-- | --: | :-- | :-- |"]
        for r in bad:
            out.append(f"| {r['stem']} | {r['page']} | {r['source']} | {r['display']} | {md_cell(','.join(r['tags']), 40)} | "
                       f"{md_cell('; '.join(r['issues']), 300)} |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- integrity audit

REQUIRED_HEADER = ("title", "source_pdf", "pdf_pages", "printed_pages", "pdf_type", "bibliography_key", "supports",
                   "provider_pages", "licence", "disagrees_with_claude", "reading_status", "used_by")
MARKER_LINE = re.compile(r"^<!--\s*page\s+(\d+)\s*(?:\|\s*printed\s+([^|>]*?))?\s*(?:\|\s*([^>]*?))?\s*-->\s*$", re.M)


def parse_header(text: str) -> dict[str, str] | None:
    """!
    @brief The top-level keys of the YAML header of an assembled file.
    @param text File content.
    @return dict|None Key to the rest of the line (`used_by` to its list joined by commas), or None without a header.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    out: dict[str, str] = {}
    key = None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.strip().startswith("- "):
            out[key] = (out[key] + "," if out[key] else "") + line.strip()[2:]
    return out


def expand_ranges(spec: str) -> set[int]:
    """!
    @brief Pages of a `1-3,5` text (quotes allowed); anything else is ignored.
    @param spec Range text.
    @return set[int] The pages.
    """
    out: set[int] = set()
    for part in re.findall(r"\d+(?:-\d+)?", spec or ""):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def header_ranges(value: str, key: str) -> set[int]:
    """!
    @brief The pages listed under `key` inside a flow mapping such as `{claude: "1-4", gemini: ""}`.
    @param value Text of the header line after the colon.
    @param key   Name inside the braces.
    @return set[int] The pages.
    """
    m = re.search(key + r':\s*"([^"]*)"', value)
    return expand_ranges(m.group(1)) if m else set()


def audit(papers: Path) -> dict:
    """!
    @brief Check the integrity of the assembled library `papers/md-final` against `papers/ocr` and `papers/pdf`.
    @details Findings have a level: `error` (the library is wrong), `warn` (stale or suspicious), `info`. The scan for
             key-like text never records the matched text, only file and line.
    @param papers Papers folder (read only).
    @return dict `findings` (list of (level, stem, text)) and `stats` (counts of stems and pages).
    """
    F: list[tuple[str, str, str]] = []
    ocr, final = papers / "ocr", papers / "md-final"
    sdata = st.load(papers)
    pdfs = {p.stem for p in (papers / "pdf").glob("*.pdf")} if (papers / "pdf").is_dir() else set()
    finals = sorted(final.glob("*.md")) if final.is_dir() else []
    prov_pages: dict[str, dict[str, set[int]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    for label in SOURCE_DIRS:
        for lab, stem, page, _ in page_files(papers, (label,)):
            prov_pages[stem][lab].add(page)
    stats = {"pdfs": len(pdfs), "md_final": len(finals), "stems_with_ocr": len(prov_pages),
             "pages_by_source": {lab: sum(len(v.get(lab, ())) for v in prov_pages.values()) for lab in SOURCE_DIRS},
             "marker_pages": collections.Counter()}
    used_dirs = ("claude", "openrouter", "gemini", "corrected")           # what assemble reads
    for f in finals:
        stem, text = f.stem, f.read_text(encoding="utf-8", errors="replace")
        head = parse_header(text)
        if head is None:
            F.append(("error", stem, "no YAML header"))
            continue
        for k in REQUIRED_HEADER:
            if k not in head:
                F.append(("error", stem, f"header field '{k}' missing"))
        if stem not in pdfs:
            F.append(("warn", stem, "md-final file without a PDF in papers/pdf"))
        total = int(head["pdf_pages"]) if head.get("pdf_pages", "").isdigit() else 0
        marks = [(m.start(), int(m.group(1)), (m.group(3) or "").strip()) for m in MARKER_LINE.finditer(text)]
        nums = [n for _, n, _ in marks]
        if nums != list(range(1, total + 1)):
            F.append(("error", stem, f"page markers {nums[:3]}...{nums[-2:]} are not 1..{total} in order without gaps"))
        # per-page chunks and states
        chunks = st.split_pages(text)
        for p in range(1, total + 1):
            stats["marker_pages"]["total"] += 1
            chunk = chunks.get(p, "")
            have = {lab: p in prov_pages[stem].get(lab, ()) for lab in used_dirs}
            if chunk.strip() == "[missing]":
                stats["marker_pages"]["missing"] += 1
                if any(have.values()):
                    F.append(("error", stem, f"p{p}: '[missing]' but a page exists in {', '.join(k for k, v in have.items() if v)}; run assemble"))
                elif p in prov_pages[stem].get("claude-whole", ()) or p in prov_pages[stem].get("retry", ()):
                    F.append(("info", stem, f"p{p}: missing in md-final; only a whole/retry page exists (assemble does not read those folders)"))
            suffix = next((s for _, n, s in marks if n == p), "")
            marker_state = "corrected" if suffix.startswith("corrected") else "verified" if suffix.startswith("verified") else "machine"
            if chunk.strip() == "[missing]":
                continue
            eff = st.effective(papers, stem, p, sdata)
            stats["marker_pages"][eff["state"]] += 1
            if eff["state"] != marker_state:
                F.append(("warn", stem, f"p{p}: marker says {marker_state}, reading_status.json says {eff['state']} (md-final is stale; run assemble)"))
            if eff["state"] == "corrected":
                cf = st.corrected_path(papers, stem, p)
                if cf.is_file():
                    want = re.sub(r"^\s*<!--\s*page\s+\d+\s*-->\s*", "", cf.read_text(encoding="utf-8"), count=1)
                    if chunk.strip() != want.strip():
                        F.append(("error", stem, f"p{p}: corrected page not used as is in md-final (text differs from ocr/corrected)"))
        if head.get("reading_status", "").startswith("{"):
            for state in ("verified", "corrected"):
                want = header_ranges(head["reading_status"], state)
                got = {p for p in range(1, total + 1) if st.effective(papers, stem, p, sdata)["state"] == state and chunks.get(p, "").strip() != "[missing]"}
                if want != got:
                    F.append(("warn", stem, f"header {state} pages {sorted(want)} differ from reading_status.json {sorted(got)} (stale; run assemble)"))
        for p in header_ranges(head.get("provider_pages", ""), "corrected"):
            if not st.corrected_path(papers, stem, p).is_file():
                F.append(("error", stem, f"p{p}: header lists a corrected page but ocr/corrected has no file"))
        miss = header_ranges(head.get("provider_pages", ""), "missing")
        if miss and head.get("used_by", "none found") not in ("none found", ""):
            F.append(("warn", stem, f"cited paper with missing pages {sorted(miss)}"))
    # sidecar entries
    for stem, ent in sorted(sdata.items()):
        if stem not in pdfs:
            F.append(("warn", stem, "reading_status.json entry for a stem without a PDF"))
        for p, e in ent.items():
            if e.get("state") == "corrected" and not st.corrected_path(papers, stem, int(p)).is_file():
                F.append(("error", stem, f"p{p}: state corrected but ocr/corrected file missing"))
            if e.get("state") not in st.STATES:
                F.append(("error", stem, f"p{p}: unknown state {e.get('state')!r}"))
    # orphans: page files of stems with no PDF, files that are not pages, pages beyond the PDF
    for stem in sorted(prov_pages):
        if stem not in pdfs:
            F.append(("warn", stem, "page files in papers/ocr without a PDF in papers/pdf (orphans)"))
        if stem in pdfs and not (final / f"{stem}.md").is_file():
            F.append(("info", stem, "page files exist but no md-final file (not assembled)"))
    for f in sorted(finals):
        head = parse_header(f.read_text(encoding="utf-8", errors="replace")) or {}
        total = int(head["pdf_pages"]) if head.get("pdf_pages", "").isdigit() else 0
        for lab, pages in prov_pages.get(f.stem, {}).items():
            beyond = sorted(p for p in pages if total and p > total)
            if beyond:
                F.append(("error", f.stem, f"{lab} page files beyond the {total} PDF pages: {beyond}"))
    if ocr.is_dir():
        odd = sorted(x.name for x in ocr.rglob("*.bak") if x.is_file())
        if odd:
            F.append(("info", "-", f"{len(odd)} backup files in papers/ocr ({', '.join(odd[:4])}...)"))
    # key-like text and confidential files in what the library holds
    scan = list(final.glob("*.md")) if final.is_dir() else []
    scan += [x for x in ocr.rglob("*") if x.is_file() and x.suffix in (".md", ".json", ".bak")] if ocr.is_dir() else []
    for f in sorted(scan):
        try:
            data = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rx in keys.KEY_PATTERNS:
            for m in rx.finditer(data):
                F.append(("error", f.stem, f"key-like text in {f.relative_to(papers)} line {data.count(chr(10), 0, m.start()) + 1} (not shown)"))
    cfg = json.loads((config.DATA / "confidential.json").read_text(encoding="utf-8"))
    known = {h.lower() for h in cfg.get("sha256", [])}
    confidential_stems = {p.stem for p in (papers / "pdf").glob("*.pdf") if config.file_sha256(p) in known} if (papers / "pdf").is_dir() else set()
    held = [x for x in ocr.rglob("*") if x.is_file()] if ocr.is_dir() else []
    held += [x for x in final.glob("*") if x.is_file()] if final.is_dir() else []
    for f in sorted(held):
        m = PAGE_FILE_RE.match(f.name)
        stem = m.group("stem") if m else f.stem
        # name patterns and the SHA-256 of the PDF with the same stem (a renamed copy has an innocent name)
        if any(re.search(p, f.name, re.I) for p in cfg["name_patterns"]) or stem in confidential_stems:
            F.append(("error", stem, f"confidential file in the library: {f.relative_to(papers)}"))
    stats["marker_pages"] = dict(stats["marker_pages"])
    return {"findings": sorted(F), "stats": stats}


def render_audit(result: dict) -> str:
    """!
    @brief The Markdown report of `audit`.
    @param result Output of `audit`.
    @return str The report text.
    """
    s, F = result["stats"], result["findings"]
    c = collections.Counter(level for level, _, _ in F)
    out = ["# Library audit", "", "Generated by `python -m tools.ocr audit` (offline, read only).", "",
           f"Findings: {c['error']} error, {c['warn']} warn, {c['info']} info.", "", "## Counts", "",
           f"* PDFs in papers/pdf: {s['pdfs']}; assembled files in md-final: {s['md_final']}; stems with page files: {s['stems_with_ocr']}",
           "* Page files by source: " + ", ".join(f"{k} {v}" for k, v in s["pages_by_source"].items()),
           "* Pages in md-final by state: " + ", ".join(f"{k} {v}" for k, v in sorted(s["marker_pages"].items())), "",
           "## Findings", ""]
    if not F:
        out.append("None.")
    else:
        out += ["| level | stem | finding |", "| :-- | :-- | :-- |"]
        out += [f"| {lv} | {md_cell(stem, 60)} | {md_cell(text, 260)} |" for lv, stem, text in F]
    return "\n".join(out) + "\n"
