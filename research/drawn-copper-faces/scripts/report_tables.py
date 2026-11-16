#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file report_tables.py
@brief Prints the Markdown tables of the README from the caches of the studies (`out/*.json`): the finite-element references, the decomposition, the boards with an outline and the records that move.
@details Run: `.venv/bin/python research/drawn-copper-faces/scripts/report_tables.py [fem|dec|dec8|fdm|outline|harness]`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import study_decomposition as SD                                          # noqa: E402

OUT = os.path.join(HERE, "..", "out")


def load(name):
    """!
    @brief Read a cache.
    @param name File name in `out/`.
    @return dict.
    """
    return json.load(open(os.path.join(OUT, name)))


def table_fem():
    """!
    @brief The finite-element references.
    @return None.
    """
    print("| board | h_side W/m2K | layers | 0.4 mm | 0.2 mm (0.3 for 4 layers) | extrapolated |\n| :-- | --: | --: | --: | --: | --: |")
    for name, hs, ly in SD.LIST:
        r = SD.fem_ref(name, hs, ly)
        if r is None:
            continue
        fem = load("fem.json")
        fine = "0.2" if f"{name}|{hs:g}|{ly}|0.2" in fem else "0.3"
        print(f"| {name} | {hs} | {ly} | {fem[f'{name}|{hs:g}|{ly}|0.4']['heater_mean']:.3f} | {fem[f'{name}|{hs:g}|{ly}|{fine}']['heater_mean']:.3f} | {r[1]:.3f} |")


def table_dec(model, tag):
    """!
    @brief The decomposition table of a model and a laminate rule.
    @param model 'fvm' or 'fdm'.
    @param tag 'n4' or 'n8'.
    @return None.
    """
    dec = load("dec.json")
    print("| board, h_side, layers | reading | 1 mm | 0.5 mm | 0.25 mm |\n| :-- | :-- | --: | --: | --: |")
    for name, hs, ly in SD.LIST:
        key = f"{model}|{name}|{hs}|{ly}|{tag}"
        if key not in dec:
            continue
        ref = SD.fem_ref(name, hs, ly)
        r = ref[1] if ref else dec[key]["faces"][-1]
        tagref = "" if ref else " (no FEM: reference is the flow reading at 0.25 mm)"
        for i, var in enumerate(SD.VARIANTS):
            lab = f"{name}, {hs}, {ly}L{tagref}" if i == 0 else ""
            print(f"| {lab} | {var} | " + " | ".join(f"{100 * (x / r - 1):+.2f}" for x in dec[key][var]) + " |")


def table_compact(model, tag):
    """!
    @brief One row per board: drawn (the program), exact fill alone, and the flow faces at the three cells, error against the reference in per cent.
    @param model 'fvm' or 'fdm'.
    @param tag 'n4' or 'n8'.
    @return None.
    """
    dec = load("dec.json")
    print("| board, h_side W/m2K, layers | drawn 1 / 0.5 / 0.25 mm | exact fill alone 1 / 0.5 / 0.25 | lambda faces 1 / 0.5 / 0.25 | flow faces 1 / 0.5 / 0.25 |\n| :-- | :-- | :-- | :-- | :-- |")
    for name, hs, ly in SD.LIST:
        key = f"{model}|{name}|{hs}|{ly}|{tag}"
        if key not in dec:
            continue
        ref = SD.fem_ref(name, hs, ly)
        r = ref[1] if ref else dec[key]["faces"][-1]
        mark = "" if ref else " (*)"
        cols = [" / ".join(f"{100 * (x / r - 1):+.1f}" for x in dec[key][v]) for v in SD.VARIANTS]
        print(f"| {name}, {hs}, {ly}{mark} | " + " | ".join(cols) + " |")


def table_outline():
    """!
    @brief The boards with an outline.
    @return None.
    """
    import numpy as np
    o = load("outline_skip.json")
    sys.path.insert(0, os.path.join(HERE, "..", "..", "imported-copper-edge-film", "scripts"))
    import study_drawn_film as S
    print("| case, h_side, cell mm | program mean / spread / worst | zones read as an import |\n| :-- | :-- | :-- |")
    for key, v in o.items():
        name, h, cell = key.split("|")
        tr = S.truth_of(name, float(h))
        ea, eb = (100 * (np.array(v[k]) / tr - 1) for k in ("base", "new"))
        print(f"| {name}, {h}, {cell} | {ea.mean():+.2f} / {np.ptp(ea):.2f} / {np.abs(ea).max():.2f} | {eb.mean():+.2f} / {np.ptp(eb):.2f} / {np.abs(eb).max():.2f} |")


def table_harness():
    """!
    @brief The records of the frozen-number boards that move.
    @return None.
    """
    h = load("harness_skip.json")
    print("| record (board, model, cell mm) | largest change K | at | rise of the hottest value K | change % of the rise | seconds before -> after |\n| :-- | --: | :-- | --: | --: | :-- |")
    nmove = ntot = 0
    for key, r in h.items():
        b, n = r["base"]["values"], r["new"]["values"]
        if b is None or n is None:
            continue
        ntot += 1
        k = max(b, key=lambda q: abs(n[q] - b[q]))
        d = n[k] - b[k]
        if abs(d) > 1e-4:
            nmove += 1
        if abs(d) > 1e-3:
            print(f"| {key} | {d:+.4f} | {k} | {b['t_max']:.2f} | {100 * d / max(b['t_max'] - 25.0, 1e-9):+.3f} | {r['base']['seconds']:.2f} -> {r['new']['seconds']:.2f} |")
    print(f"\n{ntot} records compared, {nmove} change by more than 1e-4 K")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "fem"
    {"fem": table_fem, "dec": lambda: table_compact("fvm", "n4"), "dec8": lambda: table_compact("fvm", "n8"), "fdm": lambda: table_compact("fdm", "n4"), "long": lambda: table_dec("fvm", "n4"), "outline": table_outline,
     "harness": table_harness}[what]()
