#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file config.py
@brief Paths, data files, page-range parsing and the confidential-file guard of the OCR tool.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from tools.ocr.keys import project_roots

DATA = Path(__file__).resolve().parent / "data"


def papers_dir(arg: str | None = None) -> Path:
    """!
    @brief The folder of the (git-ignored) papers library.
    @param arg Value of `--papers`, or None. Order: argument, environment PCBT_PAPERS, `papers/` of the main checkout.
    @return Path The folder (it may not exist).
    """
    if arg:
        return Path(arg).expanduser().resolve()
    if os.environ.get("PCBT_PAPERS"):
        return Path(os.environ["PCBT_PAPERS"]).expanduser().resolve()
    return project_roots()[-1] / "papers"


def models() -> dict:
    """!
    @brief The models table (default model and fallbacks per provider) from data/models.json.
    @return dict Provider name to {"default": str, "fallbacks": list[str], "note": str}.
    """
    return json.loads((DATA / "models.json").read_text(encoding="utf-8"))


def default_prompt() -> str:
    """!
    @brief The transcription prompt from data/prompt.txt.
    @return str The prompt text.
    """
    return (DATA / "prompt.txt").read_text(encoding="utf-8").strip()


def parse_pages(spec: str, total: int | None = None) -> list[int]:
    """!
    @brief Turn a page spec such as "3,5-6" into [3, 5, 6] (1-based PDF pages).
    @param spec  Comma-separated numbers and ranges; "all" needs `total`.
    @param total Number of pages of the PDF (used for "all" and for ranges ending in "-").
    @return list[int] Pages in the order given, without repeats.
    @throws ValueError On an empty or malformed spec.
    """
    spec = spec.strip().lower()
    if spec == "all":
        if not total:
            raise ValueError("'all' needs the number of pages")
        return list(range(1, total + 1))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d*)", part)
        if m:
            end = int(m.group(2)) if m.group(2) else total
            if end is None:
                raise ValueError(f"open range '{part}' needs the number of pages")
            out.extend(range(int(m.group(1)), end + 1))
        elif part.isdigit():
            out.append(int(part))
        else:
            raise ValueError(f"bad page spec '{part}'")
    if not out:
        raise ValueError("empty page spec")
    return list(dict.fromkeys(out))


_HASHES: dict[tuple[str, int, int], str] = {}


def file_sha256(path: Path) -> str | None:
    """!
    @brief SHA-256 of a file, cached by path, size and modification time.
    @param path File path.
    @return str|None Hex digest, or None when the file cannot be read (or does not exist).
    """
    try:
        st = path.stat()
        key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
        if key not in _HASHES:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            _HASHES[key] = h.hexdigest()
        return _HASHES[key]
    except OSError:
        return None


def is_confidential(pdf: Path, first_page_text: str = "", metadata: str = "") -> str | None:
    """!
    @brief Decide whether a file must not be sent to an online provider.
    @details Four checks, any of which refuses: the SHA-256 of the file is a known confidential file (catches a
             renamed copy whose text has no mark), the file name or the metadata (title, author, ...) matches a name
             pattern, or the text of the first pages or the metadata holds a marker word.
    @param pdf             Path of the PDF.
    @param first_page_text Text of its first pages (may be empty).
    @param metadata        Concatenated PDF metadata values (may be empty).
    @return str|None The reason (what matched) or None when nothing matches.
    """
    cfg = json.loads((DATA / "confidential.json").read_text(encoding="utf-8"))
    known = {h.lower() for h in cfg.get("sha256", [])}
    if known and pdf.is_file() and file_sha256(pdf) in known:
        return "the file is a known confidential file (SHA-256)"
    for pat in cfg["name_patterns"]:
        if re.search(pat, pdf.stem, re.I):
            return f"file name matches '{pat}'"
        if metadata and re.search(pat, metadata, re.I):
            return f"the PDF metadata matches '{pat}'"
    for marker in cfg["text_markers"]:
        if marker.lower() in (first_page_text + " " + metadata).lower():
            return f"the PDF text or metadata contains '{marker}'"
    return None
