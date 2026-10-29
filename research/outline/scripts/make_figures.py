#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Pictures of the outline study, written to figures/ (committed, linked from the README files).

@details fig_01: the five outline presets with the bounding box and the rectangle of the same area; fig_02: the FVM temperature map on a T-shaped board and
         on its same-area rectangle; fig_03: the error of the lumped model for the three rectangles on every outline and layout (the table of the README); fig_06: the cells off a
         round board, the board time constant with and without their pin, and the step response that the power profiles use, full length and cut short.
Usage: python research/outline/scripts/make_figures.py   (from the repository root; about 3 minutes)
"""

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)
from pcbthermal import SolverOptions, simulate                                   # noqa: E402
from pcbthermal.geometry import points_in_polygon, polygon_area                  # noqa: E402
import outline_rectangle_study as st                                             # noqa: E402
import study_outline_time_constant as tc                                         # noqa: E402

OUT = Path(HERE).parent / "figures"          # kept in the repository on purpose: the README files link to them


def fig_shapes():
    """!
    @brief The five outlines, their bounding box and the rectangle of the same area.
    @return None.
    """
    shapes = st.outlines(100.0, 80.0)
    fig, axs = plt.subplots(1, 5, figsize=(16, 3.6))
    for ax, (name, poly) in zip(axs, shapes.items()):
        pa = np.array(poly)
        s = np.sqrt(polygon_area(pa) / (100.0 * 80.0))
        ax.fill(pa[:, 0], pa[:, 1], color="#fcd9a8", ec="#b45309", lw=1.5, label="real outline")
        ax.plot([0, 100, 100, 0, 0], [0, 0, 80, 80, 0], "--", color="#6b7280", lw=1, label="bounding box")
        cx, cy = 50.0, 40.0
        ax.plot(cx + np.array([-1, 1, 1, -1, -1]) * 50 * s, cy + np.array([-1, -1, 1, 1, -1]) * 40 * s, color="#1d4ed8", lw=1.5, label="same area")
        ax.set_title(f"{name} (area ratio {s ** 2:.2f})", fontsize=9)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    # one legend under the panels: inside the first panel it covered the ellipse
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc="lower center", ncol=3)
    fig.suptitle("The outlines of the Board panel, the bounding box and the rectangle of the same area (what the lumped and analytic models use)", fontsize=10)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig_01_outlines_and_rectangles.png", dpi=110)
    plt.close(fig)


def fig_maps():
    """!
    @brief FVM temperature of the T-shaped board (centre layout) and of its same-area rectangle, same colour scale.
    @return None.
    """
    pa = np.array(st.outlines(100.0, 80.0)["T"]) / 1000.0
    real = st.with_parts(st.LAYOUTS["centre"])
    real.board.outline = pa
    rect, _s = real.equivalent_rectangle()
    res = [simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"] for p in (real, rect)]
    fields = [np.asarray(r.T)[0] for r in res]                                   # Layer 1 (top) temperature, cells off the board sit at ambient
    vmin, vmax = min(float(f.min()) for f in fields), max(float(f.max()) for f in fields)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, r, f, title in zip(axs, res, fields, ("real T outline", "rectangle of the same area")):
        im = ax.imshow(f, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)
        ax.set_title(f"{title}: Tmax {r.t_max:.1f} °C", fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=ax, label="°C", shrink=0.8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_t_outline_maps.png", dpi=110)
    plt.close(fig)


def fig_errors():
    """!
    @brief Error of the lumped model for the three rectangles on every outline and layout.
    @return None.
    """
    opt = lambda m: SolverOptions(models=(m,), cell_mm=1.0)                      # noqa: E731
    labels, data = [], []
    for name, poly in st.outlines(100.0, 80.0).items():
        pa = np.array(poly) / 1000.0
        for lay, centres in st.LAYOUTS.items():
            if not all(points_in_polygon(np.array([c[0]]), np.array([c[1]]), pa)[0] for c in centres):
                continue
            real = st.with_parts(centres)
            real.board.outline = pa
            ref = simulate(real, opt("fvm")).results["fvm"]
            plain = st.with_parts(centres)
            row = [(simulate(p, opt("lumped")).results["lumped"].t_max - ref.t_max) / ref.delta_t * 100.0 for p in (plain, real, st.scaled_box(plain, 1.1))]
            labels.append(f"{name}\n{lay}")
            data.append(row)
    data = np.array(data)
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(15, 4.6))
    for k, (lab, col) in enumerate((("bounding box", "#6b7280"), ("same area (used)", "#1d4ed8"), ("1.1 x bounding box", "#d97706"))):
        ax.bar(x + (k - 1) * 0.27, data[:, k], 0.27, label=lab, color=col)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Lumped error of Tmax (% of the FVM rise)")
    ax.set_title("Lumped model on the rectangles against the FVM on the real outline (negative = too cool)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_lumped_error_by_rectangle.png", dpi=110)
    plt.close(fig)


def fig_time_constant():
    """!
    @brief The cells off a round board (pinned to ambient), the time constant with and without the pin, and the step response full length and cut short.
    @return None.
    """
    from pcbthermal import fvm
    disc, square = tc.board(tc.ROUND), tc.board()
    net = fvm.Network(disc, 30, 30, assemble=False, with_blocks=False)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    axs[0].imshow(np.where(net.active, net.cover, np.nan), origin="lower", extent=(0, 60, 0, 60), cmap="Oranges", vmin=0, vmax=1.3)
    axs[0].imshow(np.where(net.active, np.nan, 1.0), origin="lower", extent=(0, 60, 0, 60), cmap="Greys", vmin=0, vmax=2)
    for x in np.arange(0, 60.1, 2.0):
        axs[0].plot([x, x], [0, 60], color="#d1d5db", lw=0.3)
        axs[0].plot([0, 60], [x, x], color="#d1d5db", lw=0.3)
    o = np.array(tc.ROUND + [tc.ROUND[0]])
    axs[0].plot(o[:, 0], o[:, 1], "k-", lw=1.2)
    axs[0].add_patch(plt.Rectangle((27, 27), 6, 6, fc="#dc2626", ec="k"))
    axs[0].set_title("Round board on its 2 mm grid: orange = board cover", fontsize=9)
    # The legend of the grey cells goes in the label: any place inside the panel meets the circumference
    axs[0].set_xlabel("x (mm); grey: off the board, pinned to ambient (1 W/K)")
    rows = [("square", *tc.time_constants(square)), ("round", *tc.time_constants(disc))]
    x = np.arange(2)
    axs[1].bar(x - 0.2, [r[1] for r in rows], 0.4, color="#9ca3af", label="pin counted (before)")
    axs[1].bar(x + 0.2, [r[2] for r in rows], 0.4, color="#1d4ed8", label="pin left out (now)")
    for k, r in enumerate(rows):
        axs[1].text(k - 0.2, r[1] + 2, f"{r[1]:.2f} s", ha="center", fontsize=8)
        axs[1].text(k + 0.2, r[2] + 2, f"{r[2]:.0f} s", ha="center", fontsize=8)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(["square 60 mm", "round, 59.8 mm"])
    axs[1].set_ylabel("board time constant C / G (s)")
    axs[1].set_title("The pin is not a path to the air", fontsize=9)
    # head-room for the legend: in the middle it covered a bar
    axs[1].set_ylim(0, 135)
    axs[1].legend(fontsize=8, loc="upper center", ncol=2)
    t, z, r = fvm.step_responses(disc, cell_mm=2.0)
    t0, z0, _ = fvm.step_responses(disc, cell_mm=2.0, t_end=10.0 * rows[1][1])
    axs[2].semilogx(t, z[0], "-", color="#1d4ed8", label="now: ten time constants")
    axs[2].semilogx(t0, z0[0], "-", color="#dc2626", lw=2, label="before: cut at 0.2 s")
    axs[2].axhline(r[0], color="k", ls=":", label=f"steady resistance {r[0]:.1f} K/W")
    axs[2].set_xlabel("time (s)")
    axs[2].set_ylabel("rise of the hottest point per watt (K/W)")
    axs[2].set_title("Step response used by the power profiles (FVM)", fontsize=9)
    axs[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_outline_time_constant.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the data figures (1 to 3 and 6; the diagrams 4 and 5 are drawn by make_diagrams.py).
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_shapes()
    fig_maps()
    fig_errors()
    fig_time_constant()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
