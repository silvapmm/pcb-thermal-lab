#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_fig_part_outline.py
@brief Four pictures for `docs/theory.md` 1.3: how a part that crosses the board outline is spread over the cells it cuts (fix of 2.4.5, `geometry.part_weights`).

@details fig_34: one cut cell with the part, the outline and the 8 x 8 samples coloured (part only, board only, both) and the same 8 x 8 samples as the board cover of the model;
         fig_35: the weight of that cell by three rules (product of the two covers, plain intersection, intersection normalised to the board cover) and the power density each
         puts on the board part of the cell, relative to the density of the part; fig_36: the example board cut to a T at 1 mm, FVM temperature before and after the fix, and the
         hottest point against the cell size; fig_37: error of the hottest point of a small T against the position of the cut edge (edge-shift sweep), four rules, FVM at 1 and 0.5 mm.
         Every number comes from the program (`pcbthermal`); the "before" rule is the `coverage_fraction` of the part alone (outline ignored), which the program used until 2.4.4.
         Run: .venv/bin/python research/theory/scripts/make_fig_part_outline.py (from the repository root; about 6 minutes). Writes figures/fig_34 to fig_37.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from matplotlib.patches import Polygon, Rectangle                  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "outline" / "scripts"))
from pcbthermal import Problem, fvm, geometry, model              # noqa: E402
from pcbthermal.examples import example_board                      # noqa: E402
from outline_rectangle_study import outlines                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
PART_C, BOARD_C, BOTH_C, NONE_C = "#f4a261", "#8ecae6", "#2a9d8f", "#f1f1f1"

# The cell of the first two pictures (unit square) with a slanted board edge and a part whose corner lies in it
BOARD = np.array([[-1.0, -1.0], [2.0, -1.0], [2.0, 1.0], [-1.0, -0.35]])       # the board lies below the line y = 0.1 + 0.45 x, which cuts the cell
PART = np.array([[0.45, -1.0], [2.0, -1.0], [2.0, 0.55], [0.45, 0.55]])         # a part whose corner (0.45, 0.55) lies in the cell


def cell_numbers():
    """!
    @brief The shares of the unit cell for the picture: part, board (8 x 8 and 4 x 4), both, and the three weights.
    @return dict with the counts and weights.
    """
    ns = 8
    s = (np.arange(ns) + 0.5) / ns
    gx, gy = np.meshgrid(s, s)
    part = geometry.points_in_polygon(gx, gy, PART)
    board = geometry.points_in_polygon(gx, gy, BOARD)
    both = part & board
    cover4 = float(geometry.coverage_fraction(BOARD, 1, 1, 1.0, 1.0, 4)[0, 0])
    c_part = part.mean()
    c_b = board.mean()
    share = both.sum() / board.sum()                       # share of the board part of the cell that the part covers
    return {"part": part, "board": board, "both": both, "cover4": cover4, "c_part": float(c_part), "c_b8": float(c_b),
            "inter": float(both.mean()), "share": float(share),
            "w_product": float(c_part * c_b), "w_inter": float(both.mean()), "w_norm": float(share * c_b)}


def fig_cut_cell():
    """!
    @brief Figure 34: the cut cell with its samples coloured.
    @return None.
    """
    d = cell_numbers()
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, ns, title in ((axs[0], 8, "8 x 8 samples (part and outline)"), (axs[1], 8, "8 x 8 samples (the board cover of the model)")):
        s = (np.arange(ns) + 0.5) / ns
        gx, gy = np.meshgrid(s, s)
        part = geometry.points_in_polygon(gx, gy, PART)
        board = geometry.points_in_polygon(gx, gy, BOARD)
        for x, y, p, b in zip(gx.ravel(), gy.ravel(), part.ravel(), board.ravel()):
            col = BOTH_C if (p and b) else PART_C if p else BOARD_C if b else NONE_C
            if ax is axs[1]:
                col = BOARD_C if b else NONE_C       # the cover counts the board samples only
            ax.plot(x, y, "s", color=col, ms=9, mec="#555", mew=0.4)
        ax.add_patch(Rectangle((0, 0), 1, 1, fc="none", ec="k", lw=2))
        if ax is axs[0]:
            ax.add_patch(Polygon(PART, closed=True, fc="none", ec="#c1440e", lw=2, ls="--"))
        ax.add_patch(Polygon(BOARD, closed=True, fc="none", ec="#1d4ed8", lw=2))
        ax.set_xlim(-0.12, 1.12); ax.set_ylim(-0.12, 1.12); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, fontsize=10)
    axs[0].text(0.5, -0.19, f"part {d['part'].sum()}/64, board {d['board'].sum()}/64, both {d['both'].sum()}/64   (orange: part only, blue: board only, green: both)",
                ha="center", fontsize=8.5, transform=axs[0].transData)
    axs[1].text(0.5, -0.19, f"board cover c_b = {d['board'].sum() / 64:.4f} (8 x 8, geometry.BOARD_SAMPLES); the old 4 x 4 cover read {d['cover4']:.4f}", ha="center", fontsize=8.5)
    fig.suptitle("A cell cut by the board outline (blue line) and by the edge of a part (dashed)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_34_part_cut_cell.png", dpi=110)
    plt.close(fig)


def fig_weights():
    """!
    @brief Figure 35: the weight of the cut cell by three rules, and the power density each puts on the board part of the cell.
    @return None.
    """
    d = cell_numbers()
    names = ["product\nc_part x c_b", "plain intersection\nn(part and board) / 64", "intersection x cover\n(n_both / n_board) x c_b"]
    w = [d["w_product"], d["w_inter"], d["w_norm"]]
    # Density on the board part relative to the part's own: weight divided by (board share of the cell the model conducts with) times
    # the share of the board part that the part really covers; the right answer is 1
    dens = [w[0] / (d["c_b8"] * d["share"]), w[1] / (d["c_b8"] * d["share"]), w[2] / (d["c_b8"] * d["share"])]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    cols = ["#9aa5b1", "#e9c46a", "#2a9d8f"]
    axs[0].bar(range(3), w, color=cols)
    for i, v in enumerate(w):
        axs[0].text(i, v + 0.004, f"{v:.3f}", ha="center", fontsize=9)
    axs[0].set_xticks(range(3)); axs[0].set_xticklabels(names, fontsize=8)
    axs[0].set_ylabel("weight of the cell (share of the cell)")
    axs[0].set_title("Weight given to the cut cell", fontsize=10)
    axs[1].bar(range(3), dens, color=cols)
    axs[1].axhline(1.0, color="k", lw=1)
    axs[1].set_ylim(0, 1.15)
    for i, v in enumerate(dens):
        axs[1].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    axs[1].set_xticks(range(3)); axs[1].set_xticklabels(names, fontsize=8)
    axs[1].set_ylabel("power density on the board part / density of the part")
    axs[1].set_title("Density the model puts on the board part (1 = the part's own)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_35_part_weight_rules.png", dpi=110)
    plt.close(fig)


def example_t():
    """!
    @brief The example board cut to a T (100 x 80 mm) with a side film of 10 W/m2K.
    @return Problem.
    """
    p = example_board()
    p.board.h_side = 10.0
    p.board.outline = np.array(outlines(100.0, 80.0)["T"]) / 1000.0
    return p


def old_weights(poly, outline, nx, ny, dx, dy, samples=8, cover=None):
    """!
    @brief The rule of 2.4.4 and before: the part alone, the outline ignored.
    @param poly Part polygon (m).
    @param outline Board outline (ignored).
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width (m).
    @param dy Cell height (m).
    @param samples Samples per cell side.
    @param cover Board cover (ignored).
    @return Array (ny, nx).
    """
    return geometry.coverage_fraction(poly, nx, ny, dx, dy, samples)


def fig_example_t():
    """!
    @brief Figure 36: example board cut to a T, FVM at 1 mm before and after, and the hottest point against the cell size.
    @return None.
    """
    new_pw = fvm.part_weights
    res = {}
    for tag, f in (("old", old_weights), ("new", new_pw)):
        fvm.part_weights = f
        res[tag] = fvm.solve_steady(example_t(), cell_mm=1.0)
    cells = (1.0, 2 / 3, 0.5, 1 / 3)
    series = {}
    for tag, f in (("old", old_weights), ("new", new_pw)):
        fvm.part_weights = f
        series[tag] = [fvm.solve_steady(example_t(), cell_mm=c).t_max for c in cells]
    fvm.part_weights = new_pw
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1, 1, 0.9]})
    vmin = min(float(np.nanmin(np.where(r.arrays["board_mask"], r.T[0], np.nan))) for r in res.values())
    vmax = max(r.t_max for r in res.values())
    for ax, tag, title in ((axs[0], "old", "before (2.4.4): whole-cell power on cut cells"), (axs[1], "new", "after: board part of the footprint")):
        r = res[tag]
        t = np.where(r.arrays["board_mask"], r.T[0], np.nan)
        im = ax.imshow(t, origin="lower", extent=[0, 100, 0, 80], cmap="inferno", vmin=vmin, vmax=vmax)
        ax.set_title(f"{title}\nhottest point {r.t_max:.2f} degC (FVM, 1 mm)", fontsize=9)
        ax.set_xlabel("x [mm]")
    fig.colorbar(im, ax=axs[:2], shrink=0.8, label="temperature [degC]")
    axs[2].plot(cells, series["old"], "o-", color="#c1440e", label="before (2.4.4)")
    axs[2].plot(cells, series["new"], "s-", color="#2a9d8f", label="after")
    axs[2].invert_xaxis()
    axs[2].set_xlabel("cell size [mm]"); axs[2].set_ylabel("hottest point [degC]")
    axs[2].set_title("against the cell size (the part is cut by the\noutline at 1 and 0.5 mm, not at 2/3 and 1/3 mm)", fontsize=9)
    axs[2].legend(fontsize=8); axs[2].grid(alpha=0.3)
    fig.savefig(OUT / "fig_36_part_example_t.png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return series


def tee(a, part=(9, 10, 12, 14)):
    """!
    @brief The small T board (30 x 24 mm, 2 W part over the re-entrant corner) with the neck edge at x = a mm.
    @param a Position of the left neck edge in mm (the right one is 30 - a).
    @param part Part rectangle (x0, y0, x1, y1) in mm.
    @return Problem.
    """
    b = 30.0 - a
    p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 2.0, rect=part, name="U")
    p.set_outline([[0, 12], [a, 12], [a, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    return p


def fig_edge_shift():
    """!
    @brief Figure 37: error of the hottest point against the position of the neck edge for four rules, FVM at 1 and 0.5 mm.
    @return dict of the spreads (max - min of the error) per cell and rule.
    """
    new_pw = fvm.part_weights
    inter = lambda poly, o, nx, ny, dx, dy, samples=8, cover=None: new_pw(poly, o, nx, ny, dx, dy, samples)   # noqa: E731
    cover_cls = model.Board.cover
    rules = {"before (2.4.4)": (old_weights, 4), "intersection only": (inter, 4), "fix (normalised to cover)": (new_pw, 4),
             "fix + cover sampled 8 x 8 (fix/board-cover-8x8)": (new_pw, 8)}
    styles = {"before (2.4.4)": ("o-", "#c1440e"), "intersection only": ("^--", "#e9c46a"), "fix (normalised to cover)": ("s-", "#2a9d8f"),
              "fix + cover sampled 8 x 8 (fix/board-cover-8x8)": ("d:", "#264653")}
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    spreads = {}
    for ax, (cell, n) in zip(axs, ((1.0, 12), (0.5, 12))):
        fracs = np.arange(n + 1) / n
        aa = 10.0 + fracs * cell
        fvm.part_weights = new_pw
        refs = [fvm.solve_steady(tee(a), cell_mm=1 / 24).t_max for a in aa]            # fine-grid reference with the fixed rule
        for name, (f, cs) in rules.items():
            fvm.part_weights = f
            # Pin the board cover of every rule to its own lattice: the program default (geometry.BOARD_SAMPLES) is 8 since fix/board-cover-8x8,
            # so a rule of the 4 x 4 cover must force it (the default would silently turn the three first curves into 8 x 8 ones)
            model.Board.cover = lambda self, nx, ny, dx, dy, samples=None, minimum=0.01, cs=cs: cover_cls(self, nx, ny, dx, dy, cs, minimum)
            err = np.array([fvm.solve_steady(tee(a), cell_mm=cell).t_max - r for a, r in zip(aa, refs)])
            model.Board.cover = cover_cls
            spreads[(cell, name)] = float(np.ptp(err))
            m, c = styles[name]
            ax.plot(fracs, err, m, color=c, label=f"{name} (spread {np.ptp(err):.2f} K)", ms=4)
        fvm.part_weights = new_pw
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"cell {cell:g} mm", fontsize=10)
        ax.set_xlabel("position of the cut edge, as a fraction of a cell")
        ax.set_ylabel("error of the hottest point [K]")
        ax.grid(alpha=0.3); ax.legend(fontsize=7.5)
    fig.suptitle("Small T board (30 x 24 mm, 2 W part across the re-entrant corner): FVM error against a 1/24 mm reference, edge moved by one cell", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_37_part_edge_shift.png", dpi=110)
    plt.close(fig)
    return spreads


def main():
    """!
    @brief Draw the four pictures and print the numbers they show.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    d = cell_numbers()
    print("cell:", {k: (round(v, 4) if isinstance(v, float) else None) for k, v in d.items() if not hasattr(v, "shape")})
    fig_cut_cell()
    fig_weights()
    print("example T, hottest point at cells 1, 2/3, 1/2, 1/3 mm:", fig_example_t())
    print("edge-shift spreads:", fig_edge_shift())


if __name__ == "__main__":
    main()
