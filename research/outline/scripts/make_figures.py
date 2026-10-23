"""!
@file make_figures.py
@brief Pictures of the outline study, written to figures/ (committed, linked from the README files).

@details fig_01: the five outline presets with the bounding box and the rectangle of the same area; fig_02: the FVM temperature map on a T-shaped board and
         on its same-area rectangle; fig_03: the error of the lumped model for the three rectangles on every outline and layout (the table of the README).
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
    axs[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("The outlines of the Board panel, the bounding box and the rectangle of the same area (what the lumped and analytic models use)", fontsize=10)
    fig.tight_layout()
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


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_shapes()
    fig_maps()
    fig_errors()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
