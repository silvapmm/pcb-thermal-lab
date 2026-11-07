#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of research/laminate-edge-band from the sweeps in out/ (run study_reference.py, study_sweep.py and study_harness_impact.py first): the error of the hottest rise against the edge
       coefficient for the rules (fig_04), the width of the band with and without the half-cell film (fig_05), and the cost in unknowns (fig_06).
@details Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/make_figures.py
"""

import json

import _bootband

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

HS = [10.0, 50.0, 200.0, 500.0, 2000.0]


def load(name):
    """!
    @brief Read a sweep file.
    @param name File name without extension.
    @return dict
    """
    return json.loads((_bootband.OUT / f"{name}.json").read_text())


def err(d, t, hs, pos, cell, rule):
    """!
    @brief Error of a rule on a case.
    @param d Sweep dict.
    @param t Thickness string.
    @param hs Edge coefficient.
    @param pos Position.
    @param cell Cell in mm.
    @param rule Rule name.
    @return float percent
    """
    return d[f"30|20|2|{t}|{hs}|{pos}|{cell}"][rule][0]


def fig_04():
    """!
    @brief Error against h_side, one panel per thickness, corner (solid) and centre (dashed), cell 0.5 mm.
    @return None
    """
    d = load("sweep30b")
    rules = [("default", "program as is", "k"), ("eta", "eta (no unknowns)", "tab:purple"), ("band1", "band, no half-cell film", "tab:orange"), ("margin+hc", "band + half-cell film", "tab:green")]
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.0), sharey=True)
    for ax, t in zip(axs, ("0.8", "1.6", "3.2")):
        for r, lab, c in rules:
            for pos, ls in (("corner", "-"), ("centre", "--")):
                ax.semilogx(HS, [err(d, t, h, pos, 0.5, r) for h in HS], ls, color=c, marker="o", ms=3, label=lab if pos == "corner" else None)
        ax.axhspan(-3, 3, color="tab:green", alpha=0.08)
        ax.set_title(f"2 layers, {t} mm, 30 x 20 mm, cell 0.5 mm", fontsize=9)
        ax.set_xlabel("edge coefficient (W/m2K)")
        ax.grid(alpha=0.3)
        ax.set_ylim(-30, 8)
    axs[0].set_ylabel("error of the hottest rise against the 3D reference (%)")
    axs[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(_bootband.FIGURES / "fig_04_error_against_edge_coefficient.png", dpi=105)
    plt.close(fig)


def fig_05():
    """!
    @brief The width of the band, in gap thicknesses, with and without the half-cell film (3.2 mm, corner).
    @return None
    """
    d = load("sweep30b")
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for ax, cell in zip(axs, (0.5, 0.25)):
        for hs, c in ((50.0, "tab:blue"), (200.0, "tab:orange"), (500.0, "tab:red")):
            ws = [0.0, 0.5, 1.0, 1.5, 2.0]
            plain = ["ring", "band0.5", "band1", None, "band2"]
            hc = ["ring+hc", "b0.5+hc", "b1+hc", "b1.5+hc", "b2+hc"]
            ax.plot([w for w, r in zip(ws, plain) if r], [err(d, "3.2", hs, "corner", cell, r) for r in plain if r], "--o", color=c, ms=3, alpha=0.6)
            ax.plot(ws, [err(d, "3.2", hs, "corner", cell, r) for r in hc], "-s", color=c, ms=3, label=f"h_s = {hs:g} (solid: with the half-cell film)")
        ax.set_title(f"3.2 mm, corner, cell {cell} mm", fontsize=9)
        ax.set_xlabel("band width from the edge cells (gap thicknesses)")
        ax.grid(alpha=0.3)
        ax.axhspan(-3, 3, color="tab:green", alpha=0.08)
    axs[0].set_ylabel("error (%)")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootband.FIGURES / "fig_05_band_width.png", dpi=105)
    plt.close(fig)


def fig_06():
    """!
    @brief Unknowns against the default for the rules, by thickness and cell (30 x 20 mm board), and the worst error at h_s <= 200.
    @return None
    """
    d = load("sweep30b")
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8))
    ax = axs[0]
    for r, c in (("b0.5+hc", "tab:green"), ("b1+hc", "tab:blue"), ("margin+hc", "tab:red")):
        for cell, ls in ((1.0, ":"), (0.5, "-")):
            ax.plot([0.8, 1.6, 3.2], [d[f"30|20|2|{t}|200.0|corner|{cell}"][r][1] / d[f"30|20|2|{t}|200.0|corner|{cell}"]["default"][1] for t in ("0.8", "1.6", "3.2")], ls, marker="o", color=c,
                    label=f"{r}, cell {cell}")
    ax.set_xlabel("board thickness (mm)")
    ax.set_ylabel("unknowns / unknowns of the program")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    ax.set_title("cost of the band (30 x 20 mm board)", fontsize=9)
    ax = axs[1]
    for r, c in (("default", "k"), ("eta", "tab:purple"), ("b0.5+hc", "tab:green"), ("b1+hc", "tab:blue"), ("margin+hc", "tab:red")):
        w = [max(abs(err(d, t, h, pos, cell, r)) for h in (10.0, 50.0, 200.0) for pos in ("corner", "centre") for cell in (1.0, 0.5, 0.25)) for t in ("0.8", "1.6", "3.2")]
        ax.plot([0.8, 1.6, 3.2], w, "-o", color=c, label=r)
    ax.axhline(3, color="gray", ls="--", lw=0.8)
    ax.set_xlabel("board thickness (mm)")
    ax.set_ylabel("worst |error| for h_s <= 200 (%)")
    ax.set_title("both positions, cells 1, 0.5, 0.25 mm", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootband.FIGURES / "fig_06_cost_and_worst_error.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    fig_04()
    fig_05()
    fig_06()
