#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file report.py
@brief Printing and saving helpers of the study scripts: a fixed-width table of rows, a JSON file in out/ and the 1/n fit.
@details Every study prints the numbers that go into the README (the README copies the printed table, not a retyped one) and saves the same numbers to out/<name>.json for make_figures.py.
"""

import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "out"


def save(name, obj):
    """!
    @brief Save an object as out/<name>.json (NumPy numbers and arrays are converted).
    @param name File stem.
    @param obj Dict or list.
    @return pathlib.Path of the file.
    """
    OUT.mkdir(exist_ok=True)

    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))

    path = OUT / f"{name}.json"
    path.write_text(json.dumps(obj, indent=1, default=conv))
    return path


def table(rows, cols, widths=None, title=None):
    """!
    @brief Print rows (dicts) as a table with the given columns; a float is shown with two decimals (percent errors) unless it is a (format, value) tuple.
    @param rows List of dicts.
    @param cols List of keys.
    @param widths Optional column widths.
    @param title Optional title line.
    @return str The text printed.
    """
    widths = widths or [max(len(str(c)), 8) for c in cols]
    widths[0] = max(widths[0], max(len(str(r.get(cols[0], ""))) for r in rows) if rows else 0)
    lines = [title] if title else []
    lines.append(" | ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        cells = []
        for c, w in zip(cols, widths):
            v = r.get(c, "")
            if isinstance(v, tuple):
                v = format(v[1], v[0])
            elif isinstance(v, float):
                v = f"{v:+.2f}" if abs(v) < 1e4 else f"{v:.3g}"
            cells.append(str(v).ljust(w) if c == cols[0] else str(v).rjust(w))
        lines.append(" | ".join(cells))
    text = "\n".join(lines)
    print(text, flush=True)
    return text


def fit_inverse_n(ns, errs, n_min=2):
    """!
    @brief Least-squares fit e(n) = e_inf + a / n on the points with n >= n_min (the 1/n law of the through-thickness error).
    @param ns Node counts.
    @param errs Errors in percent.
    @param n_min Smallest n used.
    @return dict with e_inf, a, rms (rms of the residual, percent points).
    """
    n = np.array([x for x in ns if x >= n_min], dtype=float)
    e = np.array([y for x, y in zip(ns, errs) if x >= n_min], dtype=float)
    A = np.stack([np.ones_like(n), 1.0 / n], axis=1)
    coef, *_ = np.linalg.lstsq(A, e, rcond=None)
    res = e - A @ coef
    return {"e_inf": float(coef[0]), "a": float(coef[1]), "rms": float(np.sqrt(np.mean(res ** 2)))}
