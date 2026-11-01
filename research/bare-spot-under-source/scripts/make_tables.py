#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_tables.py
@brief Prints the Markdown tables of the README from the result files of the study scripts (out/*.json), so that the numbers in the text are the numbers the scripts printed.
@details Usage: python research/bare-spot-under-source/scripts/make_tables.py > out/tables.md   (from the repository root, after the study scripts).
"""

import _bootstrap  # noqa: F401  (import paths)

import json

from _bootstrap import OUT

MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def pct(v, r):
    """!
    @brief Error in percent.
    @param v Value.
    @param r Reference.
    @return float.
    """
    return 100.0 * (v / r - 1.0)


def models_tables():
    """!
    @brief Tables of the five models against the window, per stack-up and cell.
    @return None (prints).
    """
    rows = json.load(open(OUT / "sweep_models.json"))
    for cell in ("0.5", "1.0"):
        print(f"\n**Cell {cell} mm: error of the peak against the resolved 3D (%), reference peak in K**\n")
        print("| Stack-up | window (mm) | reference | FVM | FDM | 3D solid | Lumped | Analytic |")
        print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
        for r in rows:
            s, w = r["name"].rsplit(" w=", 1)
            m = r["models"][cell]
            print(f"| {s} | {w} | {r['ref']['max']:.2f} | " + " | ".join(f"{pct(m[k], r['ref']['max']):+.1f}" for k in MODELS) + " |")


def treat_tables():
    """!
    @brief Table of the treatments of the FVM per stack-up and window at 0.5 and 1 mm.
    @return None (prints).
    """
    rows = json.load(open(OUT / "sweep_treat.json"))
    keys = ["program", "vert", "n=2", "n=4", "n=6", "n=2+v", "n=3+v", "n=4+v"]
    for cell in ("0.5", "1.0"):
        print(f"\n**Cell {cell} mm: FVM peak error (%) of the program and of the treatments; last column: unknowns of n=4+v over the program's**\n")
        print("| Stack-up | window | " + " | ".join(keys) + " | cost |")
        print("| :-- | --: | " + " | ".join("--:" for _ in keys) + " | --: |")
        for r in rows:
            s, w = r["name"].rsplit(" w=", 1)
            t = r["treat"][cell]
            print(f"| {s} | {w} | " + " | ".join(f"{pct(t[k]['peak'], r['ref']['max']):+.1f}" for k in keys) + f" | {t['n=4+v']['unknowns'] / t['program']['unknowns']:.2f} |")


def extra_table():
    """!
    @brief Table of the windows through every layer and the half-bare footprint.
    @return None (prints).
    """
    rows = json.load(open(OUT / "sweep_extra.json"))
    print("\n**Windows through every copper layer and half-bare footprints, cell 0.5 mm (error %)**\n")
    print("| Case | reference | FVM | FDM | 3D solid | Lumped | Analytic | vert | n=2+v | n=4+v |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for r in rows:
        m, t, ref = r["models"]["0.5"], r["treat"]["0.5"], r["ref"]["max"]
        print(f"| {r['name']} | {ref:.2f} | " + " | ".join(f"{pct(m[k], ref):+.1f}" for k in MODELS) + " | " + " | ".join(f"{pct(t[k]['peak'], ref):+.1f}" for k in ("vert", "n=2+v", "n=4+v")) + " |")


if __name__ == "__main__":
    models_tables()
    treat_tables()
    extra_table()
