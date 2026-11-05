#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file compare.py
@brief Automatic comparison of two transcriptions of the same page (digits, equations, similarity).

@details Used by `assemble` to report where a lower-priority source (OpenRouter, Gemini) disagrees with Claude (Claude
wins) and by the OpenRouter trial. A page "agrees" when its digit string matches exactly, the equation counts differ by
at most one and the text similarity is at least `MIN_SIMILARITY`.
"""

from __future__ import annotations

import difflib
import re

MIN_SIMILARITY = 0.85


def page_stats(text: str) -> dict:
    """!
    @brief Counts that describe a transcription.
    @param text Page Markdown (markers and comments are ignored).
    @return dict {"digits": digit characters in order, "equations": number of `$...$` / `$$...$$` spans, "words": int}.
    """
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return {"digits": "".join(re.findall(r"\d", body)),
            "equations": len(re.findall(r"\$\$.+?\$\$|\$[^$\n]+\$", body, flags=re.S)),
            "words": len(body.split())}


def compare_pages(reference: str, other: str) -> dict:
    """!
    @brief Compare a transcription with the reference one (Claude's).
    @param reference Reference page text.
    @param other     The other source's page text.
    @return dict digits_equal (bool), digits (n_ref, n_other), equations (n_ref, n_other), similarity (0..1, word
            level), agree (bool).
    """
    a, b = page_stats(reference), page_stats(other)
    wa = re.sub(r"<!--.*?-->", "", reference, flags=re.S).split()
    wb = re.sub(r"<!--.*?-->", "", other, flags=re.S).split()
    sim = difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio() if wa or wb else 1.0
    eq = abs(a["equations"] - b["equations"]) <= 1
    return {"digits_equal": a["digits"] == b["digits"], "digits": (len(a["digits"]), len(b["digits"])),
            "equations": (a["equations"], b["equations"]), "similarity": round(sim, 3),
            "agree": a["digits"] == b["digits"] and eq and sim >= MIN_SIMILARITY}
