#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file suspects.py
@brief Detector of suspect pages in OCR conversions and in PDF text layers, with printed and PDF page numbers.

@details A page is reported with the reasons that apply:
- `low_words`: fewer than 30 % of the median words of its file, or at most 12 words (a running header only);
- `undecoded_equations`: the converter left `formula-not-decoded` or `[illegible]`;
- `cipher`: base-36 font-cipher tokens such as `D4D6CTD7` (see cipher.py);
- `broken_font`: many upper-case/digit tokens that are not words;
- `garbage_text_layer`: the PDF's own text layer has control characters, few letters or words without vowels
  (a broken font encoding), so a text-layer extraction cannot be trusted;
- `offset`: the printed page number differs from the PDF page number (reported for every suspect page, and per
  file as the usual offset) because a reader who quotes "page 418" means the printed one.
The printed number is read from the PDF text layer (a line that is only a number, at the top or bottom of the page).
"""

from __future__ import annotations

import json
import re
import statistics
import unicodedata
from pathlib import Path

from tools.ocr import config
from tools.ocr.cipher import looks_ciphered

MARKER = re.compile(r"<!-- page (\d+) -->")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f]")


def split_markdown(text: str) -> dict[int, str]:
    """!
    @brief Split a converted file at its `<!-- page N -->` markers.
    @param text File content.
    @return dict[int, str] Page number to page text (empty when there are no markers).
    """
    parts = MARKER.split(text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def word_count(text: str) -> int:
    """!
    @brief Count words, ignoring HTML comments.
    @param text Page text.
    @return int Number of word-like runs.
    """
    return len(re.findall(r"\w+", re.sub(r"<!--.*?-->", "", text, flags=re.S)))


def garbage_text_layer(text: str) -> bool:
    """!
    @brief Whether the text layer of a PDF page looks like a broken font encoding.
    @param text Text from the PDF page.
    @return bool True if it has many control characters, few letters, or words without vowels.
    """
    if len(text.strip()) < 40:
        return False
    nonspace = len(re.sub(r"\s", "", text))
    if len(CONTROL.findall(text)) / max(1, len(text)) > 0.05:
        return True
    if sum(c.isalpha() for c in text) / max(1, nonspace) < 0.4:
        return True
    words = re.findall(r"[A-Za-z]{4,}", text)
    if len(words) >= 20 and sum(1 for w in words if not re.search(r"[aeiouyAEIOUY]", w)) / len(words) > 0.4:
        return True
    return False


def broken_font(text: str) -> bool:
    """!
    @brief Whether a converted page is dominated by upper-case/digit tokens that are not words.
    @param text Page text.
    @return bool True when more than 30 % of at least 10 tokens look like codes.
    """
    toks = re.findall(r"\S+", re.sub(r"<!--.*?-->", "", text))
    if len(toks) < 10:
        return False
    codes = [t for t in toks if len(t) >= 4 and re.fullmatch(r"[0-9A-Z]+", t) and re.search(r"\d", t)]
    return len(codes) / len(toks) > 0.3


def printed_page_number(pdf_text: str) -> int | None:
    """!
    @brief Read the printed page number from a PDF page's text.
    @param pdf_text Text layer of the page.
    @return int|None The number of a line that holds only a number (1 to 4 digits, or "Page N"), looked for in the
            first and last four lines, else the number at the end of a journal line with "Vol. N" after a separator;
            None when there is none.
    """
    lines = [ln.strip() for ln in normalise_layer(pdf_text).splitlines() if ln.strip()]
    for ln in lines[:4] + lines[-4:]:
        m = re.fullmatch(r"(?:page\s+|-\s*)?(\d{1,4})(?:\s*-)?", ln, re.I)
        if m:
            return int(m.group(1))
    # A journal footer or header with the number at one end after a separator, such as
    # "JUNE 2003, Vol. 125 / 179" or "180 / Vol. 125, JUNE 2003" (ASME; the slash often comes out as another glyph).
    for ln in lines[:3] + lines[-3:]:
        m = re.fullmatch(r".*\bVol\.?\s*\d+.*?\s[/|\u00d5]\s*(\d{1,4})", ln) or \
            re.fullmatch(r"(\d{1,4})\s*[/|\u00d5]\s.*\bVol\.?\s*\d+.*", ln)
        if m:
            return int(m.group(1))
    return None


def normalise_layer(pdf_text: str) -> str:
    """!
    @brief Normalise a PDF text layer for the page-number rules (pdfium expands ligatures, other readers do not).
    @param pdf_text Text layer of a page.
    @return str NFKC text (ligatures such as U+FB01 become `fi`) without soft hyphens and with blanks collapsed per line.
    """
    text = unicodedata.normalize("NFKC", pdf_text).replace("\u00ad", "")
    return "\n".join(re.sub(r"[ \t\u00a0]+", " ", ln) for ln in text.splitlines())


def joined_page_number(pdf_text: str) -> int | None:
    """!
    @brief Read a printed page number that the text layer joined to a running header on the same line.
    @details pdfium (unlike PyMuPDF) puts the header and its page number on one line, such as `86 Chapter 2: Heat
             conduction` or `5.3. Moduli of a composite 77`. Only the first and last two lines are looked at; the
             number must be the first or last token, a single integer of 1 to 4 digits next to words. A reading
             like this is a candidate only: `printed_numbers` keeps it when it agrees with the file's offset.
    @param pdf_text Text layer of the page.
    @return int|None The candidate number, or None.
    """
    lines = [ln.strip() for ln in normalise_layer(pdf_text).splitlines() if ln.strip()]
    for ln in lines[:2] + lines[-2:]:
        m = re.fullmatch(r"(\d{1,4})\s+(?=(?:\d+(?:\.\d+)*\.?\s+)?[A-Za-z])\S.*", ln) or \
            re.fullmatch(r"(?=(?:.*[A-Za-z]){3}).*[^\d\s]\s+(\d{1,4})", ln)
        if m:
            return int(m.group(1))
    return None


def printed_numbers(texts: dict[int, str]) -> dict[int, int]:
    """!
    @brief The printed page numbers read from the text layers of a file.
    @details Two readings are possible for a page: a number on a line of its own (`printed_page_number`) and a number
             joined to a running header (`joined_page_number`, what pdfium often gives). The offset of the file is the
             mode of pdf - number over both kinds of reading, so scattered wrong readings (a chapter number, a table
             entry) do not decide it; then each page keeps the reading that agrees with the offset, a line of its own
             first. A page with no reading that agrees keeps its own-line reading, as before. Broken layers are left out.
    @param texts Mapping 1-based PDF page to its text layer.
    @return dict[int, int] PDF page to printed number, for the pages where one was read.
    """
    usable = {p: t for p, t in texts.items() if not garbage_text_layer(t)}   # a broken layer gives random numbers
    strict = {p: printed_page_number(t) for p, t in usable.items()}
    joined = {p: joined_page_number(t) for p, t in usable.items()}
    votes = {p: n for p, n in strict.items() if n is not None}
    diffs = [d for p in usable for d in {p - n for n in (strict[p], joined[p]) if n is not None}]   # one vote per page and difference
    off = statistics.mode(diffs) if len(diffs) >= 2 and diffs.count(statistics.mode(diffs)) >= 2 else None
    if off is None:
        return votes
    out = {}
    for p in usable:
        for n in (strict[p], joined[p]):
            if n is not None and p - n == off:
                out[p] = n
                break
        else:
            if strict[p] is not None:
                out[p] = strict[p]
    return out


def page_offset(printed: dict[int, int]) -> int | None:
    """!
    @brief The usual difference between PDF and printed page numbers of a file.
    @param printed Mapping PDF page to printed number (only pages where one was found).
    @return int|None The most common (pdf - printed), when at least two pages agree; else None.
    """
    diffs = [p - n for p, n in printed.items()]
    if len(diffs) < 2:
        return None
    mode = statistics.mode(diffs)
    return mode if diffs.count(mode) >= 2 else None


def printed_page(pdf_page: int, found: int | None, offset: int | None) -> int | None:
    """!
    @brief The printed number of a page, made consistent with the file's offset.
    @details A number read from the text layer can be a table entry, a chapter number or a contents line (12 of
             the 765 numbers read on Lienhard2024 disagree with its offset of 14); when the file has an offset, the
             printed page is `pdf_page - offset`, and the number read is used only when there is no offset.
    @param pdf_page 1-based PDF page.
    @param found    Number read on the page, or None.
    @param offset   Usual pdf - printed difference of the file, or None.
    @return int|None The printed page number (None before the first printed page or when nothing is known).
    """
    if offset is None:
        return found
    return pdf_page - offset if pdf_page - offset >= 1 else None


def analyse_page(md_text: str | None, pdf_text: str | None, median_words: float) -> list[str]:
    """!
    @brief The reasons why a page is suspect (empty list: not suspect).
    @param md_text       Converted text of the page, or None.
    @param pdf_text      Text layer of the PDF page, or None.
    @param median_words  Median word count of the file's converted pages.
    @return list[str] Reason names (see the module description).
    """
    why = []
    if md_text is not None:
        w = word_count(md_text)
        if median_words and (w < 0.3 * median_words or w <= 12):
            why.append("low_words")
        if "formula-not-decoded" in md_text or "[illegible]" in md_text:
            why.append("undecoded_equations")
        if looks_ciphered(md_text):
            why.append("cipher")
        elif broken_font(md_text):
            why.append("broken_font")
    if pdf_text is not None and garbage_text_layer(pdf_text):
        why.append("garbage_text_layer")
    return why


def scan(papers: Path, only: list[str] | None = None) -> dict:
    """!
    @brief Scan the PDFs (and their conversions, when present) of a papers folder.
    @param papers Folder with `pdf/` and optionally `md/`.
    @param only   File stems to scan (default: all except confidential names).
    @return dict File stem to {"pages", "offset", "median_words", "suspect": [{"pdf_page", "printed_page", "reasons"}]}.
    """
    from . import render
    out = {}
    for pdf in sorted((papers / "pdf").glob("*.pdf")):
        if only and pdf.stem not in only:
            continue
        if config.is_confidential(pdf):
            continue
        md_file = papers / "md" / f"{pdf.stem}.md"
        md_pages = split_markdown(md_file.read_text(errors="ignore")) if md_file.is_file() else {}
        counts = {p: word_count(t) for p, t in md_pages.items()}
        med = statistics.median(counts.values()) if counts else 0
        try:
            texts = {i + 1: t for i, t in enumerate(render.page_texts(pdf))}
        except Exception:
            continue
        printed = printed_numbers(texts)
        off = page_offset(printed)
        sus = []
        for p, t in texts.items():
            why = analyse_page(md_pages.get(p), t, med)
            if why:
                sus.append({"pdf_page": p, "printed_page": printed_page(p, printed.get(p), off), "reasons": why})
        if sus or (off not in (None, 0)):
            out[pdf.stem] = {"pages": len(texts), "offset": off, "median_words": med, "suspect": sus}
    return out


def write_reports(result: dict, json_path: Path, md_path: Path) -> None:
    """!
    @brief Write the JSON and the Markdown report of a scan.
    @param result    Output of scan().
    @param json_path Where to write the JSON.
    @param md_path   Where to write the Markdown table.
    @return None
    """
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=1))
    lines = ["# Suspect pages", "",
             "Reasons: low_words, undecoded_equations, cipher, broken_font, garbage_text_layer (see tools/ocr/suspects.py). "
             "Each page is `pdf N / printed M`: the `<!-- page N -->` markers and `--pages` use the PDF number; a "
             "quotation of the paper uses the printed one. `offset` = pdf - printed of the file.", "",
             "| file | pages | offset | suspect pages (pdf / printed: reasons) |", "| :-- | --: | --: | :-- |"]
    for name, v in result.items():
        items = "; ".join(f"{s['pdf_page']} / {s['printed_page'] if s['printed_page'] is not None else '?'}: "
                          + ",".join(s["reasons"]) for s in v["suspect"])
        lines.append(f"| {name} | {v['pages']} | {v['offset'] if v['offset'] is not None else '?'} | {items} |")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n")
