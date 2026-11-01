#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of research/theory-sources (fig_01 to fig_05 and fig_13), from the libraries of the folder and the program's convection module.
@details Figure 1: Hollands horizontal-layer forms (1976, ISO 15099, `ht` code and documentation exponents). Figure 2: horizontal plate h of the program against Raithby and Hollands. Figure 3: effective
conductivity of the coupon against the number of series modes. Figure 4: Lemczyk Table 1 and Tables 2 and 3 (solver against paper). Figure 5: Zth of the Cauer ladder against its Foster components.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/make_figures.py
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "..", "figures")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import correlations as cr  # noqa: E402
import rc_ladder as rl  # noqa: E402
import study_culham_truncation as sct  # noqa: E402
import study_fill_prediction as sfp  # noqa: E402
import study_lemczyk_1992 as slm  # noqa: E402
import study_natural_convection_sources as snc  # noqa: E402


def fig_hollands():
    """!
    @brief Figure 1.
    @return None.
    """
    ra = np.logspace(3.2, 7, 60)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for lab, f in (("Hollands et al. 1976 (eq. 14)", cr.hollands_1976), ("ISO 15099 / Rohsenow 1985 (eq. 9)", cr.hollands_iso15099),
                   ("ht code, Ra^(1/3)", lambda r: cr.hollands_ht(0.71, r)), ("ht documentation, Ra^(1/5) in the log", lambda r: cr.hollands_ht(0.71, r, root=5.0))):
        ax[0].loglog(ra, [f(r) for r in ra], label=lab)
    ax[0].set_xlabel("Ra")
    ax[0].set_ylabel("Nu")
    ax[0].legend(fontsize=7)
    base = np.array([cr.hollands_iso15099(r) for r in ra])
    ax[1].semilogx(ra, [100 * (cr.hollands_ht(0.71, r) / b - 1) for r, b in zip(ra, base)], label="ht code (1/3)")
    ax[1].semilogx(ra, [100 * (cr.hollands_ht(0.71, r, root=5.0) / b - 1) for r, b in zip(ra, base)], label="ht documentation (1/5 in the log)")
    ax[1].semilogx(ra, [100 * (cr.hollands_1976(r) / b - 1) for r, b in zip(ra, base)], label="1976 form")
    ax[1].set_xlabel("Ra")
    ax[1].set_ylabel("difference from ISO 15099 (%)")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_01_hollands_forms.png"), dpi=105)
    plt.close(fig)


def fig_horizontal():
    """!
    @brief Figure 2.
    @return None.
    """
    rows = snc.part3()
    fig, ax = plt.subplots(figsize=(6.5, 4))
    sizes = sorted({(r[0], r[1]) for r in rows})
    for (a, b) in sizes:
        sel = [r for r in rows if (r[0], r[1]) == (a, b)]
        ax.plot([r[2] for r in sel], [r[6] for r in sel], "o-", label=f"{a:g} x {b:g} mm")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("surface excess over the air (K)")
    ax.set_ylabel("Raithby-Hollands minus program, % of the total h (eps 0.9)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_02_horizontal_plate_h.png"), dpi=105)
    plt.close(fig)


def fig_truncation():
    """!
    @brief Figure 3.
    @return None.
    """
    modes = (3, 7, 11, 21, 41, 101)
    k5 = [sct.effective_conductivity(5.0, m)[1] for m in modes]
    k4 = [sct.effective_conductivity(1e4, m)[1] for m in modes]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax[0].semilogx(modes, k5, "o-")
    ax[0].axhline(8.28, color="r", ls="--", label="paper 8.28")
    ax[0].set_title("h = 5 W/m2K (base case)", fontsize=9)
    ax[0].set_xlabel("modes per direction")
    ax[0].set_ylabel("effective conductivity (W/mK)")
    ax[0].legend(fontsize=7)
    ax[1].semilogx(modes, k4, "o-")
    ax[1].axhline(4.8, color="r", ls="--", label="paper plateau, read from Fig. 5 (plot)")
    ax[1].set_title("h = 1e4 W/m2K (Bi 625)", fontsize=9)
    ax[1].set_xlabel("modes per direction")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_03_culham_series_truncation.png"), dpi=105)
    plt.close(fig)


def fig_lemczyk():
    """!
    @brief Figure 4.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    import strip2d as s2
    qp, qs = [], []
    for w, t, l1, k, qa, _ in slm.TABLE1:
        qp.append(qa)
        qs.append(s2.trace_heat_flow(w * 1e-6, t * 1e-6, l1 * 1e-6, k, 10.0, 10.0, nx=200, nz=200))
    ax[0].loglog(qp, qs, "o")
    ax[0].plot([0.03, 3], [0.03, 3], "k-", lw=0.7)
    ax[0].set_xlabel("Q_a of Table 1 (W)")
    ax[0].set_ylabel("independent 2D solver (W)")
    for col, mark in zip(range(3, 7), "abcd"):
        pp, ss = [], []
        for row in slm.TABLE23:
            pp.append(row[col])
            ss.append(slm.psi(row[0], row[1], row[2], mark, n=200))
        ax[1].loglog(pp, ss, "o", label=f"case {mark}")
    ax[1].plot([0.05, 130], [0.05, 130], "k-", lw=0.7)
    ax[1].set_xlabel("Psi of Tables 2 and 3 (paper)")
    ax[1].set_ylabel("Psi, solver")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_04_lemczyk_tables.png"), dpi=105)
    plt.close(fig)


def fig_foster():
    """!
    @brief Figure 5.
    @return None.
    """
    r = np.array([0.00272144, 0.0220255, 0.00713124, 0.185679, 0.182443])
    c = np.array([9.29451e-05, 0.000514739, 0.00195047, 0.00305028, 0.0279554])
    t = np.logspace(-6, 0, 200)
    rf, tau = rl.foster(r, c)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.loglog(t, rl.zth_cauer(t, r, c), "k-", lw=2, label="Cauer ladder (matrix exponential)")
    for i in range(5):
        ax.loglog(t, rf[i] * (1 - np.exp(-t / tau[i])), "--", lw=0.8, label=f"Foster term {i + 1}: R {rf[i]:.4f}, tau {tau[i]:.2g} s")
    ax.plot([4e-3], [0.26], "rs", label="paper: Zth 0.26 K/W at 4 ms")
    ax.set_xlabel("t (s)")
    ax.set_ylabel("Zth (K/W)")
    ax.set_ylim(1e-4, 1)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_05_foster_cauer_zth.png"), dpi=105)
    plt.close(fig)


def fig_fill():
    """!
    @brief Figure 13: nnz(L) of splu against the symbolic Cholesky count in the elimination order of spilu, for the six distinct matrices of study_fill_prediction.py.
    @return None.
    """
    import scipy.sparse.linalg as spla
    from pcbthermal import fdm, fvm, solid3d
    from pcbthermal.model import load_problem

    rows = []
    for name in ("example_board", "reference_board"):
        prob = load_problem(os.path.join(ROOT, "examples", name + ".pcbt.json"))
        b = prob.board
        nx, ny = int(round(b.width * 1000.0 / 0.5)), int(round(b.height * 1000.0 / 0.5))
        for label, k in (("FVM 0.5 mm", fvm.Network(prob, nx, ny).K), ("FDM 1 mm", fdm.Network(prob, 1.0).K),
                         ("3D 2 mm", solid3d.Solid(prob, 2.0).K)):
            k = k.tocsc()
            ilu = spla.spilu(k, permc_spec=fvm.ORDERING, drop_tol=1e10, fill_factor=1)
            predicted = sfp.cholesky_count(k, np.argsort(ilu.perm_c))
            lu = spla.splu(k, permc_spec=fvm.ORDERING)
            rows.append((name.split("_")[0] + " " + label, k.shape[0], lu.L.nnz, predicted))
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    ax = axs[0]
    for lab, n, real, pred in rows:
        ax.loglog(real, pred, "o", markersize=7, label=lab)
    lim = [min(r[2] for r in rows) * 0.7, max(r[2] for r in rows) * 1.4]
    ax.plot(lim, lim, "k-", linewidth=0.8)
    ax.set_xlabel("nnz(L) of splu")
    ax.set_ylabel("symbolic count, spilu ordering")
    ax.set_title("prediction against the factor (on the line: equal)", fontsize=9)
    ax.legend(fontsize=6)
    ax = axs[1]
    for lab, n, real, pred in rows:
        ax.loglog(n, real / n, "o", markersize=7, label=lab)
    ax.set_xlabel("unknowns n")
    ax.set_ylabel("nnz(L) / n")
    ax.set_title("fill per unknown of the six matrices", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_13_fill_prediction.png"), dpi=105)
    plt.close(fig)
    for r in rows:
        print("%-24s n=%7d  splu=%9d  predicted=%9d" % r)


def main():
    """!
    @brief Draw the data figures.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    fig_hollands()
    fig_horizontal()
    fig_truncation()
    fig_lemczyk()
    fig_foster()
    fig_fill()


if __name__ == "__main__":
    main()
