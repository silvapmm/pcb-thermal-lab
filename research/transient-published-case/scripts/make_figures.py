#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the folder: fig_01 the two geometries (the T3 bar and the plate the board models can run), fig_02 the T3 curve and the convergence of the program's FEM,
       fig_03 the centre error in time of the three board models on the plate.
@details Every number drawn is printed by scripts/study_t3_and_plate.py. Usage: .venv/bin/python research/transient-published-case/scripts/make_figures.py (about 30 s).
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import exact1d as E  # noqa: E402
import study_t3_and_plate as S  # noqa: E402

OUT = os.path.join(HERE, "..", "figures")


def fig_01():
    """!
    @brief Drawing of the two geometries with their boundary conditions.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    a = ax[0]
    a.add_patch(Rectangle((0, 0), 10, 1, fc="#d9e4f2", ec="k"))
    a.axvline(8, color="C3", ls="--")
    a.text(8, 1.15, "probe x = 0.08 m", color="C3", ha="center")
    a.text(0, -0.5, "x = 0: 0 degC (held)", ha="left")
    a.text(10, -0.5, "x = 0.1 m: 100 sin(pi t / 40) degC", ha="right")
    a.text(5, 0.45, "k 35, rho 7200, c 440.5, T(x, 0) = 0, sides insulated", ha="center", fontsize=8)
    a.set_xlim(-0.5, 10.5)
    a.set_ylim(-1, 2)
    a.axis("off")
    a.set_title("T3 bar (published benchmark; femcore: held ends as films of h = 1e10)")
    b = ax[1]
    b.add_patch(Rectangle((0, 0), 10, 10, fc="#f6dcc8", ec="k"))
    b.text(5, 5, "uniform heater, 10 W\nstep at t = 0\n1 mm, k 35, rho c = 7200 x 440.5\nfaces insulated", ha="center", va="center")
    b.text(5, -0.9, "all four edges: film 1e5 W/m2K to 0 degC (the program's largest)", ha="center", fontsize=8)
    b.set_xlim(-1, 11)
    b.set_ylim(-1.8, 11)
    b.set_aspect("equal")
    b.axis("off")
    b.set_title("Plate for the FVM, FDM, Analytic (exact Robin double series)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_01_geometries.png"), dpi=130)
    plt.close(fig)


def fig_02():
    """!
    @brief T3 curve at x = 0.08 m from the exact series, and the FEM error against the number of elements.
    @return None.
    """
    t = np.linspace(0, 32, 65)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].plot(t, [E.bar_sinusoidal_end(0.08, s) for s in t], label="exact series")
    ax[0].plot([32], [36.60], "o", color="C3", label="published 36.60 (t = 32 s)")
    ax[0].set_xlabel("t (s)")
    ax[0].set_ylabel("T at x = 0.08 m (degC)")
    ax[0].legend()
    ax[0].grid(alpha=.3)
    ns = [20, 50, 100, 200, 400]
    ex = E.bar_sinusoidal_end(0.08, 32.0)
    err = [S.fem_t3(n=n) - ex for n in ns]
    ax[1].loglog(ns, np.abs(err), "o-", label="program FEM, Crank-Nicolson, 3200 steps")
    ax[1].loglog(ns, 0.19 * (20 / np.array(ns)) ** 2, "k:", label="slope -2")
    ax[1].set_xlabel("elements along the bar")
    ax[1].set_ylabel("|T - exact| at 0.08 m, 32 s (K)")
    ax[1].legend()
    ax[1].grid(alpha=.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_02_t3_curve_and_fem_convergence.png"), dpi=130)
    plt.close(fig)


def fig_03():
    """!
    @brief Centre rise of the plate in time: exact against the FVM default, the FVM with Crank-Nicolson and the Analytic.
    @return None.
    """
    from pcbthermal import fvm, analytic
    p, rc, k, th, power = S.plate_problem()
    q = power / (0.1 * 0.1 * th)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    tt = np.linspace(0.1, 92, 120)
    cen = 0.05
    ax.plot(tt, [float(E.square_plate_robin_heating(cen, cen, s, 0.1, k, rc, q, S.H_EDGE, 40)) for s in tt], "k", label="exact (Robin series)")
    for name, mod, kw in (("FVM default (log, Euler, 20 frames)", fvm, dict(n_out=20)), ("FVM log, Crank-Nicolson", fvm, dict(n_out=20, theta_scheme=0.5)),
                          ("Analytic", analytic, dict(n_out=20))):
        r = mod.solve_transient(p, 92.0, cell_mm=2.5, **kw)
        fr = np.asarray(r.frames)[:, 0]
        ny, nx = fr.shape[1:]
        ax.plot(r.times, fr[:, ny // 2, nx // 2], "o-", ms=3, label=name)
    ax.set_xlabel("t (s)")
    ax.set_ylabel("rise of the central cell (K)")
    ax.legend(fontsize=8)
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_03_plate_centre_in_time.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_01()
    fig_02()
    fig_03()
