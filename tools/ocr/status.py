#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file status.py
@brief Per-page reading status of the OCR pages (`papers/ocr/reading_status.json`) that `assemble` never overwrites.

@details The reviewer compares pages with their images and corrects some of them; that knowledge used to live only in
the hand-written headers and markers of `papers/md-final/<stem>.md`, which a new `assemble` replaced by `machine`.
The sidecar keeps it: `{stem: {page: {"state", "by", "note", "src_sha"}}}` with the state `verified` (compared with the
image or the text layer, no change needed), `corrected` (the reviewer changed the text; the corrected page is kept in
`papers/ocr/corrected/<stem>_p<N>.md` and `assemble` uses it before any provider) or `machine` (not compared; the
default of a page without an entry). `src_sha` is the hash of the provider page that was compared: if that page is
transcribed again the verified state no longer holds and `assemble` reports the page as `machine`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

STATES = ("verified", "corrected", "machine")
HEADER_RE = re.compile(r"^reading_status:\s*\{(?P<body>.*?)\}", re.M)
MARKER_RE = re.compile(r"^<!--\s*page\s+(\d+)\s*(?:\|[^>]*?)?-->\s*$", re.M)


def sidecar_path(papers: Path) -> Path:
    """!
    @brief Path of the status file.
    @param papers Papers folder.
    @return Path `papers/ocr/reading_status.json`.
    """
    return papers / "ocr" / "reading_status.json"


def corrected_path(papers: Path, stem: str, page: int) -> Path:
    """!
    @brief Path of the corrected text of a page.
    @param papers Papers folder.
    @param stem   PDF stem.
    @param page   PDF page, 1-based.
    @return Path `papers/ocr/corrected/<stem>_p<N>.md`.
    """
    return papers / "ocr" / "corrected" / f"{stem}_p{page}.md"


def sha(text: str) -> str:
    """!
    @brief Short hash of a page text (without the page marker and surrounding blanks).
    @param text Page text.
    @return str 16 hexadecimal characters.
    """
    body = re.sub(r"^\s*<!--\s*page\s+\d+\s*-->\s*(?:<!--\s*model:[^>]*-->\s*)?", "", text, count=1)
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:16]


def load(papers: Path) -> dict:
    """!
    @brief Read the sidecar.
    @param papers Papers folder.
    @return dict `{stem: {"<page>": {...}}}`, empty when the file does not exist.
    """
    p = sidecar_path(papers)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def save(papers: Path, data: dict) -> None:
    """!
    @brief Write the sidecar (sorted, atomic).
    @param papers Papers folder.
    @param data   The mapping to write.
    @return None
    """
    p = sidecar_path(papers)
    p.parent.mkdir(parents=True, exist_ok=True)
    ordered = {s: {k: data[s][k] for k in sorted(data[s], key=int)} for s in sorted(data)}
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ordered, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)


def page_state(data: dict, stem: str, page: int) -> dict:
    """!
    @brief The entry of a page.
    @param data  Sidecar mapping.
    @param stem  PDF stem.
    @param page  PDF page.
    @return dict The entry, or `{"state": "machine"}`.
    """
    return (data.get(stem) or {}).get(str(page)) or {"state": "machine"}


def split_pages(final_text: str) -> dict[int, str]:
    """!
    @brief Split an assembled Markdown into the text after each `<!-- page N ... -->` marker.
    @param final_text Content of `md-final/<stem>.md`.
    @return dict[int, str] Page number to the text of its chunk (reviewer comments included).
    """
    marks = list(MARKER_RE.finditer(final_text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(final_text)
        out[int(m.group(1))] = final_text[m.end():end].strip("\n")
    return out


def set_status(papers: Path, stem: str, pages: set[int], state: str, by: str = "reviewer", note: str = "",
               source_sha: dict[int, str] | None = None) -> None:
    """!
    @brief Record a state for pages. A `corrected` page without a corrected file takes the chunk of `md-final`.
    @param papers     Papers folder.
    @param stem       PDF stem.
    @param pages      PDF pages.
    @param state      One of `verified`, `corrected`, `machine`.
    @param by         Who compared the pages.
    @param note       Free text (what was checked or changed).
    @param source_sha Hash of the provider page per page (optional).
    @return None
    @throws ValueError For an unknown state, a `corrected` page with no corrected text to keep, or a `verified` page that does not exist.
    """
    if state not in STATES:
        raise ValueError(f"state must be one of {STATES}, not {state!r}")
    data = load(papers)
    final = papers / "md-final" / f"{stem}.md"
    chunks = split_pages(final.read_text(encoding="utf-8")) if final.is_file() else {}
    for p in sorted(pages):
        if state == "verified" and _src(papers, stem, p) is None and not corrected_path(papers, stem, p).is_file() \
                and chunks.get(p, "[missing]").strip() in ("", "[missing]"):
            # a page that does not exist cannot have been compared with its image
            raise ValueError(f"{stem} p{p}: nothing to verify (no provider page, no corrected text, not in md-final)")
        if state == "corrected":
            cf = corrected_path(papers, stem, p)
            if not cf.is_file():
                if p not in chunks or chunks[p].strip() in ("", "[missing]"):
                    raise ValueError(f"{stem} p{p}: no corrected text in ocr/corrected/ and none in md-final to keep")
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_text(f"<!-- page {p} -->\n" + chunks[p] + "\n", encoding="utf-8")
        entry = {"state": state, "by": by, "note": note}
        if source_sha and p in source_sha:
            entry["src_sha"] = source_sha[p]
        data.setdefault(stem, {})[str(p)] = entry
    save(papers, data)


def _pages(spec: str) -> set[int]:
    """!
    @brief Pages of a spec such as `1-2,4`.
    @param spec Page spec.
    @return set[int] The pages.
    """
    from .papermap import parse_page_spec
    return parse_page_spec(spec or "")


def _src(papers: Path, stem: str, page: int) -> tuple[str, str] | None:
    """!
    @brief Provider and hash of the page that `assemble` would use (Claude, then OpenRouter, then Gemini).
    @param papers Papers folder.
    @param stem   PDF stem.
    @param page   PDF page.
    @return tuple[str, str] | None (provider name, hash), or None when no provider page exists.
    """
    ocr = papers / "ocr"
    for name, f in (("claude", ocr / "anthropic" / f"{stem}_p{page}.md"), ("openrouter", ocr / "openrouter" / f"{stem}_p{page}.md"),
                    ("gemini", ocr / f"{stem}_p{page}.md")):
        if f.is_file():
            return name, sha(f.read_text(encoding="utf-8"))
    return None


def _src_sha(papers: Path, stem: str, page: int) -> str | None:
    """!
    @brief Hash of the provider page that `assemble` would use.
    @param papers Papers folder.
    @param stem   PDF stem.
    @param page   PDF page.
    @return str | None The hash, or None when no provider page exists.
    """
    src = _src(papers, stem, page)
    return src[1] if src else None


def seed(papers: Path) -> dict[str, int]:
    """!
    @brief Fill the sidecar from the hand-written work: headers and markers of `md-final` and `notes/OCR_TO_VERIFY.md`.
    @details Existing entries are never replaced. Sources, in order: the marker suffixes `| corrected and verified (image)`,
             `| verified (image)`, `| verified (text layer)`; the header `reading_status` ranges (when a marker is
             missing); the `R` pages of `OCR_TO_VERIFY.md` (verified, image) where the page in use is a Gemini page. A page with `ERROR` there and no other
             source is recorded as `machine` with the error as the note. A corrected page keeps the chunk of `md-final`
             in `ocr/corrected/`.
    @param papers Papers folder.
    @return dict[str, int] Counts of entries added per state.
    """
    from .papermap import parse_verified
    data = load(papers)
    added = {s: 0 for s in STATES}
    found: dict[str, dict[int, tuple[str, str]]] = {}
    final_dir = papers / "md-final"
    for f in sorted(final_dir.glob("*.md")) if final_dir.is_dir() else []:
        text = f.read_text(encoding="utf-8")
        d = found.setdefault(f.stem, {})
        for m in re.finditer(r"^<!--\s*page\s+(\d+)\s*\|[^|]*\|\s*(corrected and verified \(image\)|verified \(image\)|verified \(text layer\))\s*-->", text, re.M):
            kind = m.group(2)
            d[int(m.group(1))] = (("corrected" if kind.startswith("corrected") else "verified"),
                                  "text layer" if "text layer" in kind else "image")
        h = HEADER_RE.search(text)
        if h:
            for key, state, how in (("verified_image", "verified", "image"), ("corrected_then_verified", "corrected", "image"),
                                    ("verified_text_layer", "verified", "text layer")):
                m = re.search(key + r':\s*"([^"]*)"', h.group("body"))
                for p in _pages(m.group(1) if m else ""):
                    d.setdefault(p, (state, how))
    notes = papers / "notes" / "OCR_TO_VERIFY.md"
    ver = parse_verified(notes.read_text(encoding="utf-8")) if notes.is_file() else {}
    for stem, v in ver.items():
        d = found.setdefault(stem, {})
        for p in v["verified"]:
            # OCR_TO_VERIFY.md records the first pass, made on the Gemini pages: it holds for the page used now only
            # when that page is not a Claude or OpenRouter one (the Claude pass is in the md-final headers and markers).
            src = _src(papers, stem, p)
            if src is None or src[0] == "gemini":
                d.setdefault(p, ("verified", "image (OCR_TO_VERIFY.md, Gemini page)"))
    for stem, d in found.items():
        for p, (state, how) in sorted(d.items()):
            if str(p) in (data.get(stem) or {}):
                continue
            if state == "corrected" and not corrected_path(papers, stem, p).is_file():
                try:
                    set_status(papers, stem, {p}, "corrected", "reviewer", f"seeded from md-final ({how})")
                except ValueError:
                    continue
                data = load(papers)
            else:
                entry = {"state": state, "by": "reviewer", "note": f"seeded ({how})"}
                s = _src_sha(papers, stem, p)
                if s and state == "verified":
                    entry["src_sha"] = s
                data.setdefault(stem, {})[str(p)] = entry
                save(papers, data)
            added[state] += 1
    for stem, v in ver.items():
        for p in sorted(v["error"]):
            if str(p) not in (data.get(stem) or {}):
                data.setdefault(stem, {})[str(p)] = {"state": "machine", "by": "reviewer",
                                                     "note": "reviewer found an error here (OCR_TO_VERIFY.md), not corrected"}
                added["machine"] += 1
    save(papers, data)
    return added


def effective(papers: Path, stem: str, page: int, data: dict | None = None) -> dict:
    """!
    @brief The state that holds now: a verified page whose provider text changed since the check is `machine`.
    @param papers Papers folder.
    @param stem   PDF stem.
    @param page   PDF page.
    @param data   Sidecar mapping (loaded when None).
    @return dict The entry, with `state` possibly lowered and a `note` that says why.
    """
    data = load(papers) if data is None else data
    e = dict(page_state(data, stem, page))
    if e["state"] == "verified" and e.get("src_sha"):
        now = _src_sha(papers, stem, page)
        if now != e["src_sha"]:
            e.update(state="machine", note=(e.get("note", "") + "; provider page changed since the check").strip("; "))
    if e["state"] == "corrected" and not corrected_path(papers, stem, page).is_file():
        e.update(state="machine", note="corrected text file missing")
    return e
