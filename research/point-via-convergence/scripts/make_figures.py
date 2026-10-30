#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the point-via study (figures 06 and later), drawn from the outputs of the study scripts in out/ (git-ignored) and from the lattice kernel.
@details fig_06: the potential kernel of the stencil and the equivalent radius; fig_07: effective radius of a footprint against the cell; fig_08: unit-cell via effect error against
         the cell; fig_09: copper-fill gain of the 3 x 3 board against the cell; fig_10: the same on a fine series of cells; fig_11: the example board; fig_12: lone via and row;
         fig_13: the 3D solid. A figure whose input file is missing is skipped. Run the studies first (each study script says how long it takes).
Usage: python research/point-via-convergence/scripts/make_figures.py   (from the repository root)
"""

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402
import numpy as np                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import lattice                                                              # noqa: E402
import viakernel as vk                                                      # noqa: E402

OUT = HERE.parent / "figures"
DATA = HERE.parent / "out"
COL = {"program": "#d62728", "peaceman": "#9467bd", "area": "#8c564b", "tuned": "#7f7f7f", "mw_point": "#bcbd22", "mw_ring": "#17becf", "mw_area": "#2ca02c",
       "mw_tuned": "#ff7f0e", "mw_area@eta": "#2ca02c", "mw_tuned@eta": "#1f77b4"}
LAB = {"program": "program (point in one cell)", "peaceman": "independent links, Peaceman then area", "area": "independent links, area of the disc", "tuned": "independent links, tuned",
       "mw_point": "mean coupling, point + well", "mw_ring": "mean coupling, ring", "mw_area": "mean coupling, area", "mw_tuned": "mean coupling, tuned (r = r_v)",
       "mw_area@eta": "mean coupling, area, r = 0.78 r_v", "mw_tuned@eta": "mean coupling, tuned, r = 0.78 r_v (recommended)"}


def load(name):
    """!
    @brief Read a JSON output if it exists.
    @param name File name in out/.
    @return The data or None.
    """
    p = DATA / name
    return json.load(open(p)) if p.exists() else None


def fig06():
    """!
    @brief The potential kernel along the axis and the diagonal against its asymptote, and the three values of the equivalent radius.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.5, 4.2))
    n = np.arange(1, 13)
    a.plot(n, lattice.a_of(n, 0), "o-", label="exact, along an axis $a(n,0)$")
    a.plot(n, lattice.a_of(n, n), "s-", label="exact, along the diagonal $a(n,n)$")
    r = np.linspace(1, 12, 100)
    a.plot(r, 2 / np.pi * np.log(r) + lattice.KAPPA, "k--", label="$(2/\\pi)\\ln r + \\kappa$, $\\kappa$ = %.4f" % lattice.KAPPA)
    a.set_xlabel("distance in cells")
    a.set_ylabel("potential kernel $a$ (sink at 0: $\\phi(0)-\\phi(x) = a/4S$)")
    a.legend(fontsize=7)
    solve = lattice.point_sink_solve(150)
    vals = [("0.14 sqrt(2) (Peaceman 1978 estimate)", 0.14 * math.sqrt(2)), ("exp(-pi/2) (radial-flow argument)", lattice.R_EQ_PEACEMAN),
            ("exp(-(gamma + 1.5 ln 2)) (exact)", lattice.R_EQ_EXACT), ("finite solve, 301 x 301 nodes", solve["r_eq"])]
    b.barh([v[0] for v in vals], [v[1] for v in vals], color=["#bbb", "#bbb", dk_blue(), dk_blue()])
    for i, v in enumerate(vals):
        b.text(v[1] + 0.001, i, f"{v[1]:.5f}", va="center", fontsize=8)
    b.set_xlim(0.18, 0.215)
    b.set_xlabel("$r_{eq} / \\Delta x$ of a point sink on a square lattice")
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_lattice_equivalent_radius.png", dpi=105)
    plt.close(fig)


def dk_blue():
    """!
    @brief The blue of the diagram kit.
    @return Colour string.
    """
    return "#1f77b4"


def fig07():
    """!
    @brief Effective radius of the footprint (in units of the via radius) against the cell for a via at the centre, edge and corner of a cell: point, area and tuned.
    @return None.
    """
    rv = 0.15e-3
    eta = math.exp(-0.25)
    cells = np.geomspace(0.04e-3, 1.5e-3, 40)
    fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, (name, off) in zip(axs, (("cell centre", 0.5), ("cell edge", 0.0), ("cell corner", 0.0))):
        for rule, col in (("point", "#d62728"), ("area", "#2ca02c"), ("tuned (target 0.78 r_v)", "#1f77b4")):
            ys = []
            for dx in cells:
                x = (round(10e-3 / dx) + (0.5 if name == "cell centre" else 0.0)) * dx
                y = x if name != "cell edge" else (round(10e-3 / dx) + 0.5) * dx
                if rule == "point":
                    w = vk.disc_weights(x, y, 0.0, dx)
                elif rule == "area":
                    w = vk.disc_weights(x, y, rv, dx, 0.0, 24, "area")
                else:
                    w = vk.tuned_weights(x, y, eta * rv, dx) or vk.disc_weights(x, y, 0.0, dx)
                ys.append(vk.effective_radius(w, dx) / rv)
            ax.plot(cells * 1e3, ys, color=col, label=rule)
        ax.axhline(1.0, color="k", linewidth=0.7, linestyle=":")
        ax.axhline(eta, color="k", linewidth=0.7, linestyle="--")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"0.3 mm via on a {name}", fontsize=9)
    axs[0].set_ylabel("effective radius of the footprint / $r_v$")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_effective_radius_of_footprints.png", dpi=105)
    plt.close(fig)


def fig08():
    """!
    @brief Error of the via effect of the unit cell against the cell, for four cases, for the main treatments.
    @return None.
    """
    rows = load("unit_cell.json")
    if not rows:
        return
    cases = [(4.0, 0.3, 0.0), (4.0, 0.3, 385.0), (4.0, 1.0, 0.0), (4.0, 1.0, 385.0)]
    cases = [c for c in cases if any(r["task"][:3] == list(c) for r in rows)]
    fig, axs = plt.subplots(1, len(cases), figsize=(3.6 * len(cases) + 1, 4.2), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, c in zip(axs, cases):
        sel = [r for r in rows if r["task"][:3] == list(c)]
        cells = sorted({r["task"][4] for r in sel}, reverse=True)
        for tr in ("program", "peaceman", "mw_tuned", "mw_area@eta", "mw_tuned@eta"):
            ys = []
            for cell in cells:
                errs = [100 * (r["E"][tr] / r["E_ref"] - 1) for r in sel if r["task"][4] == cell]
                ys.append(max(errs, key=abs))
            ax.plot(cells, ys, "o-", color=COL[tr], label=LAB[tr], markersize=3.5, linewidth=1.3)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xscale("log")
        ax.invert_xaxis()
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"{c[1]} mm via, {'copper fill' if c[2] else 'open'}, pitch {c[0]} mm", fontsize=8.5)
    axs[0].set_ylabel("error of the via effect (percent), worst of 3 positions")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "fig_08_unit_cell_error_against_cell.png", dpi=105)
    plt.close(fig)


def fig09():
    """!
    @brief Copper-fill gain of the 3 x 3 board against the cell, FVM and FDM, with the references.
    @return None.
    """
    data = [d for d in (load("array_board_fvm.json"), load("array_board_fdm.json")) if d]
    if not data:
        return
    fig, axs = plt.subplots(1, len(data), figsize=(6.5 * len(data), 4.4), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, d in zip(axs, data):
        for tr, row in d["rows"].items():
            if tr not in COL:
                continue
            ax.plot(d["cells"], [g for _, g in row], "o-", color=COL[tr], label=LAB[tr], markersize=3.5, linewidth=1.2, alpha=1.0 if tr in ("program", "mw_tuned@eta") else 0.6)
        for k, v in d["ref"].items():
            if k.startswith("3d"):
                ax.axhline(v[1], color="k", linestyle="--", linewidth=0.8)
            else:
                ax.axhline(v[1], color="k", linestyle=":", linewidth=0.8)
        ax.set_xscale("log")
        ax.invert_xaxis()
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"{d['model'].upper()}: gain of a copper fill, 3 x 3 vias of 0.3 mm", fontsize=9)
    axs[0].set_ylabel("copper-fill gain (K)")
    axs[0].text(0.02, 0.04, "dashed: 3D with barrels drawn; dotted: fine-grid layered solver", transform=axs[0].transAxes, fontsize=7)
    axs[0].legend(fontsize=6, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_09_array_board_gain_against_cell.png", dpi=105)
    plt.close(fig)


def fig10():
    """!
    @brief Fine series of cells on the 3 x 3 board: the program and the recommended treatment.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ok = False
    for model, ls in (("fvm", "-"), ("fdm", "--")):
        rows = load(f"array_sweep_{model}.json")
        if not rows:
            continue
        ok = True
        c = [r[0] for r in rows]
        ax.plot(c, [r[1] for r in rows], "o" + ls, color=COL["program"], label=f"{model.upper()} program", markersize=3.5)
        ax.plot(c, [r[2] for r in rows], "^" + ls, color=COL["mw_area@eta"], label=f"{model.upper()} mean coupling, area", markersize=3.5)
        ax.plot(c, [r[3] for r in rows], "s" + ls, color=COL["mw_tuned@eta"], label=f"{model.upper()} mean coupling, tuned", markersize=3.5)
    if not ok:
        plt.close(fig)
        return
    ax.axhline(-4.507, color="k", linestyle=":", linewidth=0.8)
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("cell (mm)")
    ax.set_ylabel("copper-fill gain (K)")
    ax.set_title("3 x 3 via-array board, 13 cells from 1 to 0.0625 mm (dotted: fine-grid reference)", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_10_array_board_fine_sweep.png", dpi=105)
    plt.close(fig)


def fig11():
    """!
    @brief The example board: copper-fill gain against the cell, program and treatments.
    @return None.
    """
    data = [d for d in (load("example_board_fvm.json"), load("example_board_fdm.json")) if d]
    if not data:
        return
    fig, axs = plt.subplots(1, len(data), figsize=(6.2 * len(data), 4.2), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, d in zip(axs, data):
        for tr, row in d["rows"].items():
            ax.plot(d["cells"], [g for _, g in row], "o-", color=COL.get(tr, "k"), label=LAB.get(tr, tr), markersize=3.5)
        ax.set_xscale("log")
        ax.invert_xaxis()
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"example board, {d['model'].upper()}: copper-fill gain", fontsize=9)
    axs[0].set_ylabel("gain (K)")
    axs[0].legend(fontsize=6.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig_11_example_board_gain_against_cell.png", dpi=105)
    plt.close(fig)


def fig12():
    """!
    @brief Lone via and row of five: error of the via effect against the cell.
    @return None.
    """
    rows = load("row_lone_fvm.json")
    if not rows:
        return
    cases = [(1, 0.3, 0.0), (1, 0.3, 385.0), (5, 0.3, 385.0), (5, 0.6, 385.0)]
    fig, axs = plt.subplots(1, len(cases), figsize=(3.6 * len(cases) + 1, 4.2), sharey=True)
    for ax, c in zip(axs, cases):
        sel = sorted([r for r in rows if tuple(r["task"][1:4]) == c], key=lambda r: -r["task"][4])
        for tr in ("program", "peaceman", "mw_tuned", "mw_area@eta", "mw_tuned@eta"):
            ax.plot([r["task"][4] for r in sel], [100 * (r["E"][tr] / r["E_ref"] - 1) for r in sel], "o-", color=COL[tr], label=LAB[tr], markersize=3.5)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xscale("log")
        ax.invert_xaxis()
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"{c[0]} via{'s' if c[0] > 1 else ''}, {c[1]} mm, {'copper fill' if c[2] else 'open'}", fontsize=8.5)
    axs[0].set_ylabel("error of the via effect (percent)")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "fig_12_lone_via_and_row.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw every data figure whose input exists.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    for f in (fig06, fig07, fig08, fig09, fig10, fig11, fig12):
        f()
    print("written", sorted(p.name for p in OUT.glob("fig_*.png")))


if __name__ == "__main__":
    main()
