#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file papermap.py
@brief The map of the papers library: what is converted, what the theory needs, and what is still to do (`map` command).

@details Offline and read-only: it makes no network request and never touches a key. Inputs are the PDFs and the
per-page outputs of `papers/` (`ocr/anthropic` = Claude, `ocr` = Gemini, `md` = local conversion, `arxiv` = exact LaTeX
text), the notes (`INDEX.md`, `OCR_TO_VERIFY.md`, `FINAL_TRIAGE.md`, `SUSPECT_PAGES.md`) and the citations of the project
documents and of the program. Output: `notes/OCR_MAP.md` and `notes/ocr_map.json`.

Priority tiers of a page the theory relies on ("essential"): E1 = cited and not yet verified against the page image;
E2 = cited and already verified by the reviewer; O = not cited (optional). The cost estimate uses the measured rate
of `RATE_TOKENS_PER_PAGE`. The formula density of a page is a rough estimate from its text layer (equals signs and
mathematical or private-use glyphs per word), not a reading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RATE_TOKENS_PER_PAGE = 7500        # measured on 59 Claude pages (CONVERSION_PLAN.md)
DOC_FILES = ("docs/theory.md", "docs/models.md", "docs/validation.md", "docs/calculators.md",
             "research/theory/BIBLIOGRAPHY.md")
PROGRAM_DIRS = ("pcbthermal",)
CONFIDENTIAL = ("OdbppSpec81U4",)
MIN_TEXT_WORDS = 60                # a page with fewer words has no useful text layer (scan or figure page)
FORMULA_SCORE = 0.08               # (equals + math glyphs) per word above which a page is formula heavy
FORMULA_EQUALS = 10                # or this many equals signs
FREE_MAX_FORMULA_SHARE = 0.25      # a PDF is convertible from its text layer when at most this share is formula heavy
MATH_CHARS = re.compile("[\u0370-\u03ff\u2200-\u22ff\u00b1\u00d7\u2211\u221a\u222b\ue000-\uf8ff]")
CTX = 170                          # characters of context around a citation

KIND_BY_STEM = {
    "Lienhard2024": "book", "IterMethBook_2ndEd": "book", "Milton2002": "book", "eig_book_2ndEd": "book",
    "Fish2017": "thesis", "SoleymaniKoohbanani2016": "thesis", "JohansenThesis1998_EmbeddedBoundaryAlgorithms": "thesis",
    "Gerber2016Mirror": "spec", "Gerber2024": "spec", "Gerber2026": "spec", "GerberJobFormat2020": "spec",
    "XNC2021": "spec", "KiCad9PCBEditor": "spec", "SuperLUGuide": "spec", "UMFPACKGuide": "spec",
    "OdbppSpec81U4": "confidential", "siam06_short": "note", "LiSuperLUOverview_UNT": "note",
    "Khouider": "note", "Klausmeier": "note", "IsolaPrepreg": "note", "Bittele-Stackup": "note",
    "NISTIR7648": "note", "TI-AN2020": "note", "TI-SLUAAT8": "note", "TI-SPRA953B": "note", "TI-SLRR012": "note",
    "Infineon-AN2012-03": "note", "ROHM-64AN113E": "note", "ROHM-65AN114E": "note", "Johansen1997LBNL": "note",
    "McCorquodaleColellaJohansen2001": "note", "Celik2008": "note", "IIETAIntegral": "note",
}


def parse_page_spec(spec: str) -> set[int]:
    """!
    @brief Pages of a spec such as `1-2,4-8` or `5`.
    @param spec Comma-separated pages and ranges (PDF numbers).
    @return set[int] The pages.
    """
    out: set[int] = set()
    for part in re.split(r"[,\s]+", spec.strip()):
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            out.update(range(a, b + 1))
    return out


def parse_index(text: str) -> dict[str, str]:
    """!
    @brief Map every bibliography key of `notes/INDEX.md` to its PDF stem.
    @param text Content of INDEX.md (table rows `| file.pdf | key | ...`).
    @return dict[str, str] Key (and stem) to stem.
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0].endswith(".pdf"):
            continue
        stem = cells[0][:-4]
        out[stem] = stem
        for key in re.split(r"\s*/\s*", cells[1]):
            key = key.strip().strip("()")
            if re.fullmatch(r"[A-Za-z][\w.-]*", key):
                out.setdefault(key, stem)
    return out


def parse_verified(text: str) -> dict[str, dict]:
    """!
    @brief Read `OCR_TO_VERIFY.md`: the pages listed per file, those compared as right (R) and those found wrong (ERROR).
    @param text Content of the notes file.
    @return dict[str, dict] Per stem: `listed`, `verified` and `error` sets of PDF pages.
    """
    out: dict[str, dict] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not re.fullmatch(r"[\w.-]+", cells[0]) or cells[0] == "file" \
                or not re.fullmatch(r"[\d,\s-]+", cells[1]):
            continue
        d = out.setdefault(cells[0], {"listed": set(), "verified": set(), "error": set()})
        d["listed"] |= parse_page_spec(cells[1])
        note = cells[-1]
        for seg in re.split(r";", note):
            seg = seg.strip()
            m = re.match(r"((?:p\d+(?:-\d+)?[,\s]*)+)\s+(R|ERROR)\b", seg)
            if m:
                pages = parse_page_spec(re.sub(r"p", "", m.group(1)).replace(" ", ","))
                d["verified" if m.group(2) == "R" else "error"] |= pages
            else:
                # "p4 R (...); p5 ERROR: ..." inside one segment, or "R: 323, 325" for the books
                m2 = re.match(r"R:\s*([\d,\s]+)", seg)
                if m2:
                    d["verified"] |= parse_page_spec(m2.group(1))
    return out


def parse_offsets(text: str) -> dict[str, int]:
    """!
    @brief Read the PDF minus printed page offset of every file from `SUSPECT_PAGES.md`.
    @param text Content of the notes file.
    @return dict[str, int] Stem to offset (files whose offset is unknown are left out).
    """
    out: dict[str, int] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"-?\d+", cells[2]):
            out[cells[0]] = int(cells[2])
    return out


def parse_flags(text: str) -> dict[str, dict[int, str]]:
    """!
    @brief Read the flagged-page table of `FINAL_TRIAGE.md`.
    @param text Content of the notes file.
    @return dict[str, dict[int, str]] Stem to {page: flag text}.
    """
    out: dict[str, dict[int, str]] = {}
    for line in text.split("## Flagged pages")[-1].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[1].isdigit():
            out.setdefault(cells[0], {})[int(cells[1])] = cells[3][:120]
    return out


def formula_score(text: str) -> tuple[float, int]:
    """!
    @brief Rough formula density of a page from its text layer.
    @param text Text layer of one page.
    @return tuple (score = (equals signs + math or private-use glyphs) per word, number of equals signs).
    """
    words = max(1, len(re.findall(r"\w+", text)))
    eq = text.count("=")
    return (eq + len(MATH_CHARS.findall(text))) / words, eq


def citations(text: str, key: str) -> list[str]:
    """!
    @brief The contexts in which a key is cited in a text.
    @param text Document or source text.
    @param key  Citation key (matched as a whole word, so `Muzychka2003` does not match `Muzychka2003Part1`).
    @return list[str] A window of `CTX` characters on each side of every citation.
    """
    pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(key) + r"(?![A-Za-z0-9])")
    return [text[max(0, m.start() - CTX):m.end() + CTX] for m in pat.finditer(text)]


def cited_locations(ctx: str) -> dict[str, list[int]]:
    """!
    @brief Page, table, equation and figure numbers quoted in the context of a citation.
    @param ctx Context window.
    @return dict[str, list[int]] Keys `pages`, `tables`, `eqs`, `figs`.
    """
    pages: list[int] = []
    for m in re.finditer(r"\b(?:pp?\.|pages?)\s*(\d{1,4})(?:\s*(?:-|\u2013|to)\s*(\d{1,4}))?", ctx):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        pages += list(range(a, min(b, a + 12) + 1)) if b >= a else [a]
    tables = [int(x) for x in re.findall(r"\bTables?\s+(\d{1,2})", ctx)]
    eqs = [int(x) for x in re.findall(r"\beq(?:uation)?s?\.?\s*\(?(\d{1,3})", ctx, re.I)]
    figs = [int(x) for x in re.findall(r"\bFig(?:ure)?s?\.?\s*(\d{1,2})", ctx)]
    return {"pages": pages, "tables": tables, "eqs": eqs, "figs": figs}


def locate(kind: str, number: int, pages: dict[int, str]) -> list[int]:
    """!
    @brief Find the pages where a table caption or an equation number appears in the best text of each page.
    @param kind   `table` or `eq`.
    @param number Table or equation number.
    @param pages  Mapping PDF page to its best text.
    @return list[int] Pages that hold it (empty when not found).
    """
    if kind == "table":
        pat = re.compile(r"(?im)^[\s*#|]*Table\s+" + str(number) + r"\b")
    else:
        pat = re.compile(r"\(\s*" + str(number) + r"\s*\)\s*(?:\$\$|\\\]|$)", re.M)
    return [p for p, t in sorted(pages.items()) if pat.search(t)]


def page_files(folder: Path, stem: str) -> dict[int, Path]:
    """!
    @brief The per-page outputs `<stem>_p<N>.md` of a folder.
    @param folder Output folder.
    @param stem   PDF stem.
    @return dict[int, Path] Page to file.
    """
    out: dict[int, Path] = {}
    for f in folder.glob(f"{stem}_p*.md"):
        m = re.fullmatch(re.escape(stem) + r"_p(\d+)\.md", f.name)
        if m:
            out[int(m.group(1))] = f
    return out


def analyse_pdf(path: Path) -> dict:
    """!
    @brief Page count and per-page text-layer facts of a PDF (PyMuPDF).
    @param path PDF file.
    @return dict `pages`, `text` (page to text), `words`, `garbage`, `formula` (score) and `equals` per page.
    """
    import pymupdf
    from . import suspects
    doc = pymupdf.open(str(path))
    res = {"pages": len(doc), "text": {}, "words": {}, "garbage": {}, "formula": {}, "equals": {}}
    for i in range(len(doc)):
        t = doc[i].get_text()
        p = i + 1
        res["text"][p] = t
        res["words"][p] = len(re.findall(r"\w+", t))
        res["garbage"][p] = suspects.garbage_text_layer(t)
        res["formula"][p], res["equals"][p] = formula_score(t)
    doc.close()
    return res


def classify_kind(stem: str, pages: int) -> str:
    """!
    @brief The kind of a document: paper, note, book, spec, thesis or confidential.
    @param stem  PDF stem.
    @param pages Page count.
    @return str The kind.
    """
    if stem in KIND_BY_STEM:
        return KIND_BY_STEM[stem]
    return "book" if pages > 150 else "paper"


def text_class(info: dict, p: int) -> str:
    """!
    @brief Class of a page's text layer: `clean`, `formula`, `garbage` or `none`.
    @param info Result of `analyse_pdf`.
    @param p    PDF page.
    @return str The class (`formula` = clean text but formula heavy, so only the equations need the model).
    """
    if info["garbage"][p]:
        return "garbage"
    if info["words"][p] < MIN_TEXT_WORDS:
        return "none"
    if info["formula"][p] >= FORMULA_SCORE or info["equals"][p] >= FORMULA_EQUALS:
        return "formula"
    return "clean"


def build_map(papers: Path, root: Path, analyser=analyse_pdf) -> dict:
    """!
    @brief Build the whole map.
    @param papers   Papers folder.
    @param root     Repository root (documents and program sources).
    @param analyser Function reading a PDF (replaceable in tests).
    @return dict `rows` (one per PDF), `summary` and `top`.
    """
    notes = papers / "notes"
    rd = lambda p: p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""  # noqa: E731
    keymap = parse_index(rd(notes / "INDEX.md"))
    verified = parse_verified(rd(notes / "OCR_TO_VERIFY.md"))
    offsets = parse_offsets(rd(notes / "SUSPECT_PAGES.md"))
    flags = parse_flags(rd(notes / "FINAL_TRIAGE.md"))
    arxiv_pdfs = set(re.findall(r"\|\s*([\w.-]+)\.pdf\s*\|", rd(papers / "arxiv" / "INDEX.md")))
    docs = {f: rd(root / f) for f in DOC_FILES}
    program = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                        for d in PROGRAM_DIRS for p in (root / d).rglob("*.py"))
    # Status letter per key: the table of docs/theory.md first, then the first status word of the bibliography entry.
    status: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*\[([\w.-]+)\][^|]*\|[^|]*\|\s*([RSMNL])\b", docs["docs/theory.md"], re.M):
        status.setdefault(m.group(1), m.group(2))
    bib = docs["research/theory/BIBLIOGRAPHY.md"]
    for m in re.finditer(r"^### \[([\w.-]+)\][^\n]*\n(.*?)(?=^### |\Z)", bib, re.M | re.S):
        s = re.search(r"\*\*([RSMNL])\*\*", m.group(2))
        if s:
            status.setdefault(m.group(1), s.group(1))
    keys_of: dict[str, set[str]] = {}
    for k, s in keymap.items():
        keys_of.setdefault(s, set()).add(k)
    rows = []
    for pdf in sorted((papers / "pdf").glob("*.pdf")):
        stem = pdf.stem
        confidential = stem in CONFIDENTIAL
        info = {"pages": 0, "text": {}, "words": {}, "garbage": {}, "formula": {}, "equals": {}} if confidential \
            else analyser(pdf)
        n = info["pages"]
        if confidential:
            import pymupdf
            n = len(pymupdf.open(str(pdf)))
        claude = page_files(papers / "ocr" / "anthropic", stem)
        gemini = page_files(papers / "ocr", stem)
        local_text = rd(papers / "md" / f"{stem}.md")
        local = set(re.findall(r"<!-- page (\d+) -->", local_text))
        local_pages = {int(x) for x in local}
        is_arxiv = stem in arxiv_pdfs
        kind = classify_kind(stem, n)
        cls = {p: text_class(info, p) for p in range(1, n + 1)} if not confidential else {}
        counts = {c: sum(1 for v in cls.values() if v == c) for c in ("clean", "formula", "garbage", "none")}
        born = n > 0 and not confidential and (counts["garbage"] + counts["none"]) / n < 0.3
        # citations of the stem (all its keys) in the documents and the program
        ks = keys_of.get(stem, {stem})
        ndoc = {f: sum(len(citations(t, k)) for k in ks) for f, t in docs.items()}
        nprog = sum(len(citations(program, k)) for k in ks)
        cited = (sum(ndoc.values()) + nprog) > 0 or stem in verified
        # best text per page for locating tables and equations
        best = {}
        for p in range(1, n + 1):
            f = claude.get(p) or gemini.get(p)
            best[p] = f.read_text(encoding="utf-8", errors="replace") if f else info["text"].get(p, "")
        off = offsets.get(stem)
        ess: dict[int, list[str]] = {}
        for t in docs.values():
            for k in ks:
                for ctx in citations(t, k):
                    loc = cited_locations(ctx)
                    for pg in loc["pages"]:
                        # a page quoted in a document is the printed one: shift it by the file's offset when known
                        cand = pg + off if off is not None and 1 <= pg + off <= n else (pg if 1 <= pg <= n else None)
                        if cand is not None:
                            ess.setdefault(cand, []).append(f"p.{pg}")
                    for num in loc["tables"]:
                        for pg in locate("table", num, best):
                            ess.setdefault(pg, []).append(f"Table {num}")
                    for num in loc["eqs"]:
                        for pg in locate("eq", num, best)[:2]:
                            ess.setdefault(pg, []).append(f"eq. {num}")
        if stem in verified:
            for pg in verified[stem]["listed"]:
                if pg <= n:
                    ess.setdefault(pg, []).append("listed by the reviewer notes")
        if cited and not ess and not confidential and not is_arxiv and kind in ("paper", "note", "thesis"):
            # cited as a whole: the formula-heavy pages are the ones that carry numbers
            heavy = [p for p in range(1, n + 1) if cls.get(p) in ("formula", "garbage", "none")][:12]
            for pg in heavy or range(1, min(n, 6) + 1):
                ess.setdefault(pg, []).append("cited, no page given: formula-heavy page (estimate)")
        v = verified.get(stem, {"verified": set(), "error": set()})
        page_rows = []
        for pg in sorted(ess):
            ok_verified = pg in v["verified"] and pg not in v["error"]
            needs_model = (not born) or cls.get(pg) != "clean" or any(
                r.startswith(("Table", "eq.", "listed")) for r in ess[pg])
            has_claude = pg in claude
            tier = "E2" if ok_verified else "E1"
            page_rows.append({"page": pg, "tier": tier, "why": sorted(set(ess[pg]))[:4], "claude": has_claude,
                              "gemini": pg in gemini, "needs_model": needs_model, "error": pg in v["error"],
                              "flag": flags.get(stem, {}).get(pg, "")})
        e1 = [r for r in page_rows if r["tier"] == "E1"]
        if is_arxiv or confidential:
            e1 = []
        run = [r for r in e1 if r["needs_model"] and (not r["claude"] or r["error"])]
        verify_only = [r for r in e1 if r["claude"] and not r["error"] and r["needs_model"]]
        e2 = [r for r in page_rows if r["tier"] == "E2"]
        row = {
            "stem": stem, "keys": sorted(ks), "pages": n, "kind": kind,
            "born_digital": bool(born), "arxiv_text": is_arxiv, "confidential": confidential,
            "claude_pages": len(claude), "gemini_pages": len(gemini),
            "local_only_pages": len(local_pages - set(claude) - set(gemini)),
            "text_clean": counts.get("clean", 0), "text_formula": counts.get("formula", 0),
            "text_garbage_or_none": counts.get("garbage", 0) + counts.get("none", 0),
            "cited_docs": ndoc, "cited_program": nprog, "bib_status": status.get(sorted(ks)[0], "") if ks else "",
            "essential_pages": [r["page"] for r in page_rows],
            "e1_run": [r["page"] for r in run], "e1_verify_only": [r["page"] for r in verify_only],
            "e1_text_only": [r["page"] for r in e1 if not r["needs_model"]],
            "e2_pages": [r["page"] for r in e2], "flagged": sorted(flags.get(stem, {})),
            "detail": page_rows,
            "tokens_e1": len(run) * RATE_TOKENS_PER_PAGE,
        }
        row["free_text_ok"] = bool(born and not confidential and n > 0 and counts["formula"] / n <= FREE_MAX_FORMULA_SHARE
                                   and counts["garbage"] + counts["none"] == 0 and not is_arxiv)
        row["status"] = ("confidential: never sent" if confidential else
                         "arXiv text: no OCR needed" if is_arxiv else
                         "gap" if run else
                         "to verify" if verify_only else
                         "done" if page_rows else "optional")
        rows.append(row)
    total_pages = sum(r["pages"] for r in rows)
    run_pages = sum(len(r["e1_run"]) for r in rows)
    summary = {
        "pdfs": len(rows), "pages": total_pages,
        "claude_pages": sum(r["claude_pages"] for r in rows), "gemini_pages": sum(r["gemini_pages"] for r in rows),
        "essential_pages": sum(len(r["essential_pages"]) for r in rows if not (r["arxiv_text"] or r["confidential"])),
        "e1_run_pages": run_pages, "e1_verify_only_pages": sum(len(r["e1_verify_only"]) for r in rows),
        "e1_text_only_pages": sum(len(r["e1_text_only"]) for r in rows),
        "e2_pages": sum(len(r["e2_pages"]) for r in rows),
        "tokens_e1": run_pages * RATE_TOKENS_PER_PAGE,
        "optional_pages": total_pages - sum(len(r["essential_pages"]) for r in rows),
        "free_text_pdfs": [r["stem"] for r in rows if r["free_text_ok"]],
        "free_text_pages": sum(r["pages"] for r in rows if r["free_text_ok"]),
        "free_text_formula_pages": sum(r["text_formula"] for r in rows if r["free_text_ok"]),
        "rate_tokens_per_page": RATE_TOKENS_PER_PAGE,
    }
    ranked = sorted((r for r in rows if r["e1_run"]),
                    key=lambda r: (-(len(r["e1_run"]) * (1 + sum(r["cited_docs"].values()) + r["cited_program"]))))
    top = [{"stem": r["stem"], "pages": r["e1_run"], "tokens": r["tokens_e1"], "why": sorted(
        {w for d in r["detail"] if d["page"] in r["e1_run"] for w in d["why"]})[:3],
        "status": r["bib_status"]} for r in ranked[:25]]
    return {"summary": summary, "top": top, "rows": rows}


def _fmt_pages(pages: list[int], limit: int = 14) -> str:
    """!
    @brief Compact page list for a table cell.
    @param pages PDF pages.
    @param limit Maximum numbers shown before `...`.
    @return str Text such as `1-3,7,9`.
    """
    out, pages = [], sorted(pages)
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out[:limit]) + ("..." if len(out) > limit else "")


def render_markdown(m: dict) -> str:
    """!
    @brief The Markdown text of the map.
    @param m Result of `build_map`.
    @return str The document.
    """
    s = m["summary"]
    L = ["# OCR map (generated by `python -m tools.ocr map`; do not edit)", "",
         "Essential = the pages that the theory, the models, the validation, the calculators, the bibliography "
         "(statuses S, M, N, or R on a machine transcription) and the program rely on (equations, tables, constants, "
         "figures with numbers), found from the page, table and equation numbers quoted next to each citation key "
         "(printed pages shifted by the file's offset) and from the reviewer's list. Heuristic: a page missing here may "
         "still matter, and a page listed may have been cited loosely. E1 = essential and not verified against the page "
         "image; E2 = essential and verified; O = not cited.", "",
         "## Summary", "",
         f"* PDFs: {s['pdfs']}; pages: {s['pages']}; pages with a Claude output: {s['claude_pages']}; with a Gemini "
         f"output: {s['gemini_pages']}.",
         f"* Essential pages (outside arXiv and confidential files): {s['essential_pages']}; E2 (verified): {s['e2_pages']}; "
         f"optional pages (not essential): {s['optional_pages']}.",
         f"* E1 still to run with Claude (needs the model, no Claude output or a transcription found wrong): "
         f"**{s['e1_run_pages']} pages, about {s['tokens_e1']:,} tokens** at {s['rate_tokens_per_page']} per page.",
         f"* E1 with a Claude page but not verified (costs a reviewer's reading, no tokens): {s['e1_verify_only_pages']}; "
         f"E1 pages the text layer covers (prose, no table or equation quoted): {s['e1_text_only_pages']}.",
         f"* PDFs whose whole text can come free from the text layer: {len(s['free_text_pdfs'])} (list below; {s['free_text_pages']} pages, of which about {s['free_text_formula_pages']} are formula heavy and still need the model).", "",
         "## Top 25 essential gaps", "", "| # | stem | PDF pages | why | tokens | bib |", "| --: | :-- | :-- | :-- | --: | :-: |"]
    for i, t in enumerate(m["top"], 1):
        L.append(f"| {i} | {t['stem']} | {_fmt_pages(t['pages'])} | {'; '.join(t['why'])} | {t['tokens']:,} | {t['status']} |")
    L += ["", "## PDFs convertible for free from the text layer", "",
          "Born-digital, no garbage or empty page, at most 25 % formula-heavy pages (estimate): extract the text with "
          "PyMuPDF/markitdown and send only the pages marked `formula` in the table to the model.", "",
          ", ".join(s["free_text_pdfs"]) or "none", "",
          "## Every PDF", "",
          "Columns: pp = pages; type = born-digital (dig) or scan; arX = arXiv LaTeX text exists; Cl, Ge, loc = pages "
          "done by Claude, by Gemini, by the local conversion only; txt = pages with a clean text layer / formula-heavy "
          "(estimate) / garbage or empty; ess = essential pages; E1run = pages to run with Claude; E1ver = Claude page "
          "not verified; E2 = verified; flag = pages flagged by the triage; tok = tokens for E1run.", "",
          "| stem | kind | pp | type | arX | Cl | Ge | loc | txt | ess | E1run | E1ver | E2 | flag | tok | status |",
          "| :-- | :-- | --: | :-- | :-: | --: | --: | --: | :-- | --: | :-- | --: | --: | --: | --: | :-- |"]
    for r in m["rows"]:
        L.append(f"| {r['stem']} | {r['kind']} | {r['pages']} | {'dig' if r['born_digital'] else 'scan'} | "
                 f"{'yes' if r['arxiv_text'] else ''} | {r['claude_pages']} | {r['gemini_pages']} | {r['local_only_pages']} | "
                 f"{r['text_clean']}/{r['text_formula']}/{r['text_garbage_or_none']} | {len(r['essential_pages'])} | "
                 f"{_fmt_pages(r['e1_run'], 6)} | {len(r['e1_verify_only'])} | {len(r['e2_pages'])} | {len(r['flagged'])} | "
                 f"{r['tokens_e1']:,} | {r['status']} |")
    L.append("")
    return "\n".join(L)


def write_map(papers: Path, root: Path, analyser=analyse_pdf) -> tuple[Path, Path]:
    """!
    @brief Build the map and write `notes/OCR_MAP.md` and `notes/ocr_map.json`.
    @param papers   Papers folder.
    @param root     Repository root.
    @param analyser Function reading a PDF (replaceable in tests).
    @return tuple The two files written.
    """
    m = build_map(papers, root, analyser)
    (papers / "notes").mkdir(exist_ok=True)
    md, js = papers / "notes" / "OCR_MAP.md", papers / "notes" / "ocr_map.json"
    md.write_text(render_markdown(m), encoding="utf-8")
    js.write_text(json.dumps(m, indent=1, default=sorted), encoding="utf-8")
    return md, js
