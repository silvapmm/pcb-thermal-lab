#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures with data of research/analytic-edge-spatial: the eigenfunctions of the convective edge, temperature profiles through a corner part, the error of each treatment over the 135 boards, the step response.

@details fig_03 the first modes (cosine against Robin) and the wavenumbers; fig_04 the profile of the top layer through the part of a 100 x 80 mm board (FVM, faces, Robin,
         strips); fig_05 the errors of the 135 boards of study_edge_variants.py (read from out/edge_variants.txt: run the study first); fig_06 the step response of a board; fig_07 (review) faces and Robin on the boards outside the study (read from out/review_checks.txt).
         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/make_figures.py  (about 1 minute after the study)
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402
import numpy as np                      # noqa: E402

import analytic_edge as ae              # noqa: E402
import cases                            # noqa: E402
from robin_basis import Basis           # noqa: E402
from pcbthermal import SolverOptions, simulate   # noqa: E402

FIG = os.path.join(ROOT, "figures")


def fig_03():
    """!
    @brief The first Robin eigenfunctions against the cosines, and the wavenumbers for several edge parameters.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    L = 1.0
    x = np.linspace(0, L, 400)
    for k, (bl, col) in enumerate(((0.0, "k"), (4.0, "tab:blue"), (30.0, "tab:red"))):
        b = Basis(L, bl / L, 4)
        P = b.evaluate(x)
        for m in range(3):
            axs[0].plot(x, P[:, m] / np.abs(P[:, m]).max() + 2.6 * m, color=col, linewidth=1.3, label=f"beta L = {bl:g}" if m == 0 else None)
    axs[0].set_title("First three modes: cosine (beta = 0) and Robin edge, beta L = 4 and 30", fontsize=9)
    axs[0].set_yticks([])
    axs[0].set_xlabel("x / L")
    axs[0].legend(fontsize=7)
    m = np.arange(12)
    for bl, col in ((0.0, "k"), (0.5, "tab:green"), (4.0, "tab:blue"), (30.0, "tab:red")):
        b = Basis(L, bl / L, 12)
        axs[1].plot(m, b.lam * L / np.pi, "o-", color=col, markersize=3, label=f"beta L = {bl:g}")
    axs[1].set_xlabel("mode m")
    axs[1].set_ylabel("lambda_m L / pi (cosine: m)")
    axs[1].set_title("The wavenumber of the Robin basis moves from m pi/L towards (m + 1) pi/L", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_robin_modes.png"), dpi=105)
    plt.close(fig)


def fig_04():
    """!
    @brief Top-layer profile through a corner part, 100 x 80 mm, 2 x 3.2 mm, h_side 200.
    @return None.
    """
    p, (x0, y0) = cases.board(100, 80, 2, 3.2, 200.0, "corner")
    res = simulate(p, SolverOptions(cell_mm=0.5, models=("fvm",))).results["fvm"]
    row = int((y0 + 5.0) / 0.5)
    xs = (np.arange(res.T.shape[2]) + 0.5) * 0.5
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(xs, res.T[0, row, :] - cases.T0, "k", linewidth=2, label="FVM 0.5 mm (reference)")
    for name, col in (("faces", "tab:orange"), ("robin", "tab:blue"), ("strips", "tab:green")):
        r = ae.solve(p, 1.0, edge=name)
        xa = (np.arange(r["T"].shape[2]) + 0.5) * 1.0
        ax.plot(xa, r["T"][0, int((y0 + 5.0) / 1.0), :] - cases.T0, color=col, linestyle="--", label=f"Analytic, {name}")
    ax.set_xlabel("x (mm), along the line through the part, from the corner")
    ax.set_ylabel("rise of the top layer (K)")
    ax.set_title("Corner part, 100 x 80 mm, 2 layers, 3.2 mm, h_side 200 W/m2K", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_profile_corner.png"), dpi=105)
    plt.close(fig)


def fig_05():
    """!
    @brief Errors against the FVM of the 135 boards, per treatment and edge coefficient (reads out/edge_variants.txt).
    @return None.
    """
    path = os.path.join(ROOT, "out", "edge_variants.txt")
    if not os.path.exists(path):
        print("fig_05 skipped: run study_edge_variants.py first")
        return
    pat = re.compile(r"hs\s+(\d+) .*none\s+([+-][\d.]+) faces\s+([+-][\d.]+) robin\s+([+-][\d.]+) strips\s+([+-][\d.]+)")
    rows = [list(map(float, m.groups())) for m in (pat.search(l) for l in open(path)) if m]
    r = np.array(rows)
    fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharey=False)
    for ax, hs in zip(axs, (10.0, 50.0, 200.0)):
        s = r[:, 0] == hs
        ax.boxplot([r[s, 2], r[s, 3], r[s, 4]], tick_labels=["faces\n(program)", "Robin", "strips 1 mm"], showfliers=True)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(f"h_side {hs:g} W/m2K ({s.sum()} boards)", fontsize=9)
        ax.set_ylabel("error of the hottest rise against FVM 0.5 mm (%)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_05_errors_by_treatment.png"), dpi=105)
    plt.close(fig)


def fig_06():
    """!
    @brief Step response of a 60 x 40 mm board with a corner part: FVM, the program, faces, none, Robin.
    @return None.
    """
    from pcbthermal.api import step_response
    p, _ = cases.board(60, 40, 2, 1.6, 200.0, "corner")
    sr = step_response(p, "fvm", SolverOptions(models=("fvm",), cell_mm=2.0))
    t, z = np.asarray(sr.times, dtype=float), np.asarray(sr.z[0], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.semilogx(t[t > 0], z[t > 0], "k", linewidth=2, label="FVM 2 mm")
    for name, col in (("none", "tab:gray"), ("faces", "tab:orange"), ("robin", "tab:blue")):
        times, zz, rth, t63 = ae.step_response(p, name)
        ax.semilogx(times, zz, color=col, linestyle="--", label=f"Analytic, {name} (t63 {t63:.0f} s)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("rise per watt of the part (K/W)")
    ax.set_title("Unit step, corner part, 60 x 40 mm, h_side 200 W/m2K", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_06_step_response.png"), dpi=105)
    plt.close(fig)


def fig_07():
    """!
    @brief Review: faces against Robin on the boards outside the study (advanced stack-ups, partial copper on one side, one layer), by edge share (reads out/review_checks.txt).
    @return None.
    """
    path = os.path.join(ROOT, "out", "review_checks.txt")
    if not os.path.exists(path):
        print("fig_07 skipped: run study_review_checks.py --part 3 first")
        return
    rows = [l.strip().split("|") for l in open(path) if l.strip()]
    groups = {}
    for r in rows:
        key = ("advanced stack-up, full copper" if r[0].startswith("advanced") and "partial" not in r[0] and "0.2" not in r[0]
               else "one layer" if r[0] == "1 L" else "partial copper on some layers")
        groups.setdefault(key, []).append((float(r[5]), float(r[6]), float(r[7]), r[2]))
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    for ax, col, title in ((axs[0], 1, "faces (the program now)"), (axs[1], 2, "Robin, one common edge parameter")):
        for (name, pts), colour in zip(sorted(groups.items()), ("tab:blue", "tab:red", "tab:green")):
            for share, *err, pos in pts:
                ax.plot(share, err[col - 1], "o" if pos == "corner" else "s", color=colour, markersize=5, alpha=0.8)
            ax.plot([], [], "o", color=colour, label=name)
        ax.plot([], [], "ko", label="part in a corner")
        ax.plot([], [], "ks", label="part at the centre")
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xlabel("edge share sum(h_edge) / h_tot")
        ax.set_title(title, fontsize=9)
    axs[0].set_ylabel("error of the hottest rise against FVM 0.5 mm (%)")
    axs[1].legend(fontsize=7)
    fig.suptitle("Review: 54 boards outside the study (60 x 40 mm, h_side 10, 50, 200 W/m2K)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_07_review_unequal_layers.png"), dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw all the data figures.
    @return int 0.
    """
    os.makedirs(FIG, exist_ok=True)
    fig_03()
    fig_04()
    fig_05()
    fig_06()
    fig_07()
    return 0


if __name__ == "__main__":
    sys.exit(main())
