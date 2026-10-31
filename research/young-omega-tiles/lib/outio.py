#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file outio.py
@brief Small helpers shared by the studies: JSON results in the git-ignored `out/` folder (read by `make_figures.py`) and Markdown tables printed to the screen.
"""

import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def save(name, obj):
    """!
    @brief Write a result to `out/<name>.json`.
    @param name File name without extension.
    @param obj JSON-serialisable object.
    @return str Path written.
    """
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, default=float)
    return path


def load(name):
    """!
    @brief Read a result written by `save`.
    @param name File name without extension.
    @return The object.
    @throws FileNotFoundError If the study has not been run.
    """
    with open(os.path.join(OUT, name + ".json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def table(headers, rows, aligns=None):
    """!
    @brief Print a Markdown table.
    @param headers List of column titles.
    @param rows List of rows (lists of values already formatted as text).
    @param aligns Optional string of 'l'/'r' per column (default: first left, the rest right).
    @return None.
    """
    aligns = aligns or "l" + "r" * (len(headers) - 1)
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(":--" if a == "l" else "--:" for a in aligns) + " |")
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |", flush=True)
    print()
