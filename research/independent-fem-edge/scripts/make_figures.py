#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of research/independent-fem-edge from the caches: the finite-element temperature field at the cooled wall (fig_03), the grid convergence of the plate in the two methods (fig_04), and the program against the finite-element value (fig_05).
@details Reads `out/fem_cache.jsonl`, `out/fv.json`, `out/prog.json` (run `study_fem_cases.py fem`, `study_references.py fv|prog` first) and solves the 1000 W/m2K plate once at 0.1 mm for the field.
         Run (repository root): `.venv/bin/python research/independent-fem-edge/scripts/make_figures.py`. Figures are numbered after those of `make_diagrams.py` (fig_01, fig_02).
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, os.path.join(FOLDER, ".."))
import boards                                                      # noqa: E402
import conv                                                        # noqa: E402

OUT = os.path.join(FOLDER, "out")
FIG = os.path.join(FOLDER, "figures")


def fig_03():
    """!
    @brief The finite-element field of the plate at 1000 W/m2K: plan map of the top copper and the section through the wall at y = 3 mm.
    @return None.
    """
    m, hm, tc = boards.strong_edge(1000.0, hf=0.1, n_gap=8)
    T = m.solve()["T"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    X, Y = np.meshgrid(m.xn * 1e3, m.yn * 1e3)
    c = ax[0].pcolormesh(X, Y, T[0], shading="gouraud", cmap="inferno")
    fig.colorbar(c, ax=ax[0], label="rise K (top face)")
    ax[0].set_aspect("equal")
    ax[0].set_title("top copper, half board (y = 5 mm is the symmetry plane)", fontsize=8)
    ax[0].set_xlabel("x mm")
    ax[0].set_ylabel("y mm")
    j = int(np.argmin(np.abs(m.yn * 1e3 - 3.0)))
    xs = m.xn * 1e3
    sel = xs > 8.5
    XX, ZZ = np.meshgrid(xs[sel], m.zn * 1e3)
    c2 = ax[1].pcolormesh(XX, ZZ, T[:, j, sel], shading="gouraud", cmap="inferno")
    ax[1].invert_yaxis()
    ax[1].set_title("section through the wall x = 10 mm at y = 3 mm (z down)", fontsize=8)
    ax[1].set_xlabel("x mm")
    ax[1].set_ylabel("z mm")
    fig.colorbar(c2, ax=ax[1], label="rise K")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_fem_field_at_the_wall.png"), dpi=105)
    plt.close(fig)


def fig_04():
    """!
    @brief Plate at 1000 W/m2K: hottest rise against the plan size, finite element (extrapolating to 24.35 K) and the cell-centred reference (from above), with the 1/h line.
    @return None.
    """
    cache = conv._load()
    fv = json.load(open(os.path.join(OUT, "fv.json")))
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    hf = (0.2, 0.1, 0.05)
    f = [cache["strong|" + json.dumps(dict(h_side=1000.0, hf=h, n_gap=8), sort_keys=True)]["tmax"] for h in hf]
    ax[0].plot(hf, f, "o-", color="#1f77b4", label="finite element (8 bricks per gap)")
    ext = conv.richardson(*f)["ext"]
    ax[0].axhline(ext, color="#1f77b4", ls=":", lw=1)
    cell = (0.25, 0.125)
    g = [fv[f"1000.0|None|{c * 1e-3}"]["tmax"] for c in cell]
    ax[0].plot(cell, g, "s-", color="#c0392b", label="cell-centred finite volume (ref3d, 8 slabs)")
    ax[0].set_xscale("log")
    ax[0].set_xlabel("plan size near the wall, mm")
    ax[0].set_ylabel("hottest top-copper rise, K")
    ax[0].legend(fontsize=7)
    ax[0].set_title(f"plate, h_side 1000: FEM extrapolates to {ext:.2f} K", fontsize=8)
    rows = []
    for h in (200.0, 1000.0):
        e = json.load(open(os.path.join(OUT, "report.json")))[f"plate|{h}"]["ext"]
        rows.append([100 * (fv[f"{h}|None|{c * 1e-3}"]["tmax"] / e - 1) for c in cell])
    ax[1].bar(np.arange(2) - 0.18, [r[0] for r in rows], 0.35, label="FV 1/4 mm", color="#e6a0a0")
    ax[1].bar(np.arange(2) + 0.18, [r[1] for r in rows], 0.35, label="FV 1/8 mm", color="#c0392b")
    ax[1].set_xticks([0, 1])
    ax[1].set_xticklabels(["200", "1000"])
    ax[1].set_xlabel("h_side W/m2K")
    ax[1].set_ylabel("FV reference above the FEM value, %")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_convergence_two_methods.png"), dpi=105)
    plt.close(fig)


def fig_05():
    """!
    @brief The program's error against the finite-element value and against the finite-volume reference (plate at 0.25 mm with 2 and 8 sub-gaps, physical slabs; via effect; the turned square and T).
    @return None.
    """
    rep = json.load(open(os.path.join(OUT, "report.json")))
    pr = json.load(open(os.path.join(OUT, "prog.json")))
    fv = json.load(open(os.path.join(OUT, "fv.json")))
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    labels, a_fem, a_fv = [], [], []
    for h in (200.0, 1000.0):
        for n, ph, tag in ((None, False, "default, simple"), (None, True, "default, physical"), (8, True, "8 sub-gaps, physical")):
            v = pr[f"strong|{h}|None|0.25|{n}|{ph}|fvm"]
            labels.append(f"{int(h)}: {tag}")
            a_fem.append(100 * (v / rep[f"plate|{h}"]["ext"] - 1))
            a_fv.append(100 * (v / fv[f"{h}|None|0.000125"]["tmax"] - 1))
    x = np.arange(len(labels))
    ax[0].bar(x - 0.2, a_fem, 0.4, label="vs FEM", color="#1f77b4")
    ax[0].bar(x + 0.2, a_fv, 0.4, label="vs FV 1/8 mm", color="#c0392b")
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(labels, rotation=60, ha="right", fontsize=6)
    ax[0].set_title("plate, FVM 0.25 mm, error %", fontsize=8)
    ax[0].legend(fontsize=7)
    labels, a_fem, a_fv = [], [], []
    for h, d in ((200.0, 0.16), (1000.0, 0.16), (1000.0, 3.0)):
        for n, ph, tag in ((None, True, "default"), (8, True, "8 sub-gaps")):
            e = (pr[f"strong|{h}|None|0.25|{n}|{ph}|fvm"] - pr[f"strong|{h}|{d}|0.25|{n}|{ph}|fvm"])
            labels.append(f"{int(h)}, {d} mm: {tag}")
            a_fem.append(100 * (e / rep[f"via|{h}|{d}"]["ext"] - 1))
            a_fv.append(100 * (e / (fv[f"{h}|None|0.000125"]["tmax"] - fv[f"{h}|{d * 1e-3}|0.000125"]["tmax"]) - 1))
    x = np.arange(len(labels))
    ax[1].bar(x - 0.2, a_fem, 0.4, color="#1f77b4")
    ax[1].bar(x + 0.2, a_fv, 0.4, color="#c0392b")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(labels, rotation=60, ha="right", fontsize=6)
    ax[1].set_title("via effect, physical slabs, 0.25 mm, error %", fontsize=8)
    labels, a_fem, a_fv = [], [], []
    import study_report as sr                                      # noqa: F401  (for the truth lookups below)
    truth = {"sq_in|200.0": 57.2469, "sq_in|1000.0": 39.026, "sq_wall|200.0": 50.6194, "sq_wall|1000.0": 30.1046, "T_wall|200.0": 67.2415}
    for key in truth:
        v = pr[f"{key}|1.0"]
        labels.append(key.replace("|", " "))
        a_fem.append(100 * (np.mean(v) / rep[key]["ext"] - 1))
        a_fv.append(100 * (np.mean(v) / truth[key] - 1))
    x = np.arange(len(labels))
    ax[2].bar(x - 0.2, a_fem, 0.4, color="#1f77b4", label="vs FEM")
    ax[2].bar(x + 0.2, a_fv, 0.4, color="#c0392b", label="vs FV truth")
    ax[2].set_xticks(x)
    ax[2].set_xticklabels(labels, rotation=60, ha="right", fontsize=6)
    ax[2].set_title("turned squares and T, program 1 mm, mean of 10 boards, error %", fontsize=8)
    ax[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_05_program_against_fem.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    sys.path.insert(0, HERE)
    fig_03()
    fig_04()
    fig_05()
