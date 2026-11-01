#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rare_features.py
@brief Counting the rare Gerber features in a file: aperture transformations (LM, LR, LS), aperture blocks (AB), step and repeat (SR), regions (G36), arcs (G02/G03), the moire and thermal macro primitives, X2/X3 attributes.
@details The independent reader of research/gerber-import refuses what it does not implement (aperture blocks and the transformations LM, LR, LS, the moire primitive 6, image offset/mirror/scale/rotation).
         Whether that matters depends on how often real files use those features; this module counts them in the text so that the study can answer from the files, not from the specification.
         Pure text scan (regular expressions on the extended commands), no dependency; a count is the number of commands, not of objects.
"""

import re
from pathlib import Path

FEATURES = {
    "LM (aperture mirroring)": r"%LM[NXYX]{1,2}\*%",
    "LR (aperture rotation)": r"%LR-?[\d.]+\*%",
    "LS (aperture scaling)": r"%LS[\d.]+\*%",
    "AB (aperture block)": r"%ABD\d+\*%",
    "SR (step and repeat)": r"%SRX\d+Y\d+I[\d.]+J[\d.]+\*%",
    "region (G36)": r"^G36\*",
    "arc (G02/G03)": r"G0[23]\*|G0[23]X",
    "moire macro (6)": r"^6,",
    "thermal macro (7)": r"^7,",
    "outline macro (4)": r"^4,",
    "vector line macro (20)": r"^20,",
    "center line macro (21)": r"^21,",
    "polygon aperture (P)": r"%ADD\d+P,",
    "X2 file attribute (TF)": r"%TF\.",
    "X2 aperture function (TA)": r"%TA\.AperFunction",
    "X2 net attribute (TO.N)": r"%TO\.N,",
    "X3 component attribute (TO.C)": r"%TO\.C,",
    "X3 pin attribute (TO.P)": r"%TO\.P,",
    "image polarity negative (IPNEG)": r"%IPNEG\*%",
    "deprecated: image offset/mirror/scale/rotate (OF, MI, SF, IR)": r"%(OF|MI|SF|IR)",
    "deprecated: axis select (AS)": r"%AS(AY|BX)",
}


def count(text):
    """!
    @brief Count every feature in a Gerber text.
    @param text File content.
    @return dict feature name -> number of occurrences (zero counts included).
    """
    return {name: len(re.findall(rx, text, re.M)) for name, rx in FEATURES.items()}


def count_file(path):
    """!
    @brief Count the features of a file.
    @param path File path.
    @return dict as in `count`.
    """
    return count(Path(path).read_text(errors="replace"))


def summarise(per_file):
    """!
    @brief How many files use each feature.
    @param per_file Dict file name -> dict of counts (from count_file).
    @return dict feature -> (number of files that use it, total count, first three file names).
    """
    out = {}
    for name in FEATURES:
        users = [f for f, c in per_file.items() if c.get(name, 0) > 0]
        out[name] = (len(users), sum(c.get(name, 0) for c in per_file.values()), users[:3])
    return out
