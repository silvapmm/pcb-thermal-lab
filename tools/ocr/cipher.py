#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cipher.py
@brief Decoder for the base-36 font cipher of some old PDFs (seen in Muzychka2003Part1 and Part2).

@details The text of those PDFs comes out of the converter as pairs of base-36 digits, for example `D4D6CTD7`:
each pair is the code of one character plus 360, so `int("D4", 36) - 360 = 112 = "p"`, and `D4D6CTD7` reads "pres".
Only printable ASCII (32 to 126) is decoded; a token that does not decode entirely to such characters and mostly
letters is left as it is, which keeps ordinary upper-case words (`RESOLUTION`) untouched. Symbols of the math
fonts are not in this cipher and stay as they are. Optional post-processor: `python -m tools.ocr transcribe`
does not use it; call `decode_text` or `python -m tools.ocr decode FILE`.
"""

from __future__ import annotations

import re

OFFSET = 360
LIGATURES = {11: "ff", 12: "fi", 13: "fl", 14: "ffi", 15: "ffl"}   # TeX font codes below 32, seen as ADD9DC = "flux"
_TOKEN = re.compile(r"\b(?:[0-9A-Z]{2})+\b")


def decode_token(token: str) -> str | None:
    """!
    @brief Decode one token of base-36 pairs.
    @param token Even-length string of 0-9A-Z.
    @return str|None The decoded text, or None if some pair is outside printable ASCII or the result is not mostly letters.
    """
    if len(token) % 2:
        return None
    chars = []
    for i in range(0, len(token), 2):
        code = int(token[i:i + 2], 36) - OFFSET
        if code in LIGATURES:
            chars.append(LIGATURES[code])
        elif 32 <= code <= 126:
            chars.append(chr(code))
        else:
            return None
    out = "".join(chars)
    letters = sum(c.isalpha() for c in out)
    # A real cipher word is mostly letters; this rejects accidental matches such as "2024" or "A1B2".
    return out if letters >= max(1, len(out) * 0.5) else None


def decode_text(text: str) -> tuple[str, int]:
    """!
    @brief Decode every cipher token of a text.
    @param text Text from a converter.
    @return tuple[str, int] (decoded text, number of tokens decoded).
    """
    count = [0]

    def repl(m: re.Match) -> str:
        """!
        @brief Replace one match.
        @param m The regular-expression match.
        @return str The decoded token or the original.
        """
        dec = decode_token(m.group(0))
        if dec is None:
            return m.group(0)
        count[0] += 1
        return dec

    return _TOKEN.sub(repl, text), count[0]


def looks_ciphered(text: str, threshold: float = 0.3) -> bool:
    """!
    @brief Whether a page is mostly cipher tokens (used by the suspect-page detector).
    @param text Page text.
    @param threshold Fraction of whitespace-separated tokens that decode.
    @return bool True when at least `threshold` of at least 5 tokens decode.
    """
    toks = text.split()
    if len(toks) < 5:
        return False
    hits = sum(1 for t in toks if len(t) >= 4 and _TOKEN.fullmatch(t) and decode_token(t) is not None)
    return hits / len(toks) >= threshold
