#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the drawn-copper study, from the caches of the studies (`out/dec.json`, `out/fem.json`, `out/harness_skip.json`): (fig_03) the error of the four readings of the same copper
       against the finite-element reference; (fig_04) the records of the frozen-number boards that move when the zones are read as an import.
@details Run the studies first (`study_fem_reference.py`, `study_decomposition.py` with and without `--n8` and `--fdm`, `study_harness_shift.py`), then
         `.venv/bin/python research/drawn-copper-faces/scripts/make_figures.py`. Writes `figures/fig_03_decomposition.png` and `figures/fig_04_harness_shift.png`.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                           # noqa: E402
import numpy as np                                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import study_decomposition as SD                                          # noqa: E402

OUT = os.path.join(HERE, "..", "out")
FIG = os.path.join(HERE, "..", "figures")
COL = {"drawn": "#b03030", "fill": "#e0a030", "lambda": "#8080c0", "faces": "#2a7a4a"}
CASES = [("plain_inset", 200, 2), ("plain_inset", 1000, 2), ("stripes", 200, 2), ("stripes", 1000, 2), ("ell", 200, 2), ("plain_inset", 200, 4)]


def fig_decomposition():
    """!
    @brief Figure 3: error against the finite elements of the drawn copper (program), the exact fill alone, the lambda faces and the flow faces, FVM at 0.5 mm, four and eight sub-gaps.
    @return None.
    """
    dec = json.load(open(os.path.join(OUT, "dec.json")))
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, tag, title in zip(axs, ("n4", "n8"), ("default laminate rule (4 sub-gaps)", "8 sub-gaps")):
        x = np.arange(len(CASES))
        for k, var in enumerate(("drawn", "fill", "lambda", "faces")):
            err = []
            for name, hs, ly in CASES:
                v = dec[f"fvm|{name}|{hs}|{ly}|{tag}"][var][1]                      # 0.5 mm
                ref = SD.fem_ref(name, hs, ly)[1]
                err.append(100 * (v / ref - 1))
            ax.bar(x + (k - 1.5) * 0.2, err, 0.2, color=COL[var], label={"drawn": "drawn zones (program)", "fill": "exact fill, harmonic faces", "lambda": "exact fill, lambda faces",
                                                                         "faces": "exact fill, flow faces (the import rule)"}[var])
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{n}\n{h}, {l}L" for n, h, l in CASES], fontsize=8)
        ax.set_title(f"FVM 0.5 mm, {title}", fontsize=10)
        ax.set_ylabel("heater mean against the finite elements, %")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8, loc="lower center", ncol=4)
    fig.suptitle("Figure 3. The same copper read four ways (label: edge film W/m2K, copper layers)", fontsize=11)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(FIG, "fig_03_decomposition.png"), dpi=130)
    plt.close(fig)


def fig_harness():
    """!
    @brief Figure 4: the largest temperature shift of every board, model and cell of the frozen-number boards.
    @return None.
    """
    h = json.load(open(os.path.join(OUT, "harness_skip.json")))
    rows = []
    for key, r in h.items():
        if r["base"]["values"] is None or r["new"]["values"] is None:
            continue
        d = max(abs(r["new"]["values"][k] - r["base"]["values"][k]) for k in r["base"]["values"])
        if d > 1e-3:
            rows.append((key, d))
    rows.sort(key=lambda t: -t[1])
    fig, ax = plt.subplots(figsize=(9, 0.28 * len(rows) + 1.5))
    ax.barh([k for k, _ in rows][::-1], [d for _, d in rows][::-1], color="#2a7a4a")
    ax.set_xscale("log")
    ax.set_xlabel("largest change of a temperature of the record, K (only records above 1e-3 K)")
    ax.set_title("Figure 4. Records of the frozen-number boards that move (board | model | cell mm)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_harness_shift.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_decomposition()
    fig_harness()
