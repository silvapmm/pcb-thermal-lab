#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of `research/fin-channel-sources/`: Elenbaas data against the correlations (02), the array of Bar-Cohen, Iyengar and Kraus (03), the Prandtl function of the vertical plate (04) and the measured horizontal arrays (05).
@details Reads `out/source_checks.json` written by `study_source_checks.py` (run it first); one numbering with `make_diagrams.py` (01 and 06 are drawn there).
         Run: .venv/bin/python research/fin-channel-sources/scripts/make_figures.py (from the repository root).
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import sources as S                                                # noqa: E402
import channel as ch                                               # noqa: E402

OUT = HERE.parent / "figures"
DATA = HERE.parent / "out" / "source_checks.json"


def fig_02(res):
    """!
    @brief Elenbaas (1942) parallel-plate data (plot values read from Figure 11 of YTM 2002) against the correlations of the review and the independent numerical channel.
    @param res Loaded JSON.
    @return None.
    """
    a = res["A"]
    ra, nu = np.array(a["ra"]), np.array(a["nu"])
    x = np.logspace(-1, 5, 300)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axs[0]
    for name, f, ls in (("Elenbaas (8)", ch.nu_elenbaas, "-"), ("Churchill (20)", ch.nu_churchill, ":"), ("Bar-Cohen-Rohsenow (21)", ch.nu_bcr, "--"),
                        ("Raithby-Hollands (22)", ch.nu_rh, "-."), ("YTM (29)", S.ytm_parallel_plates_nu, "-")):
        ax.loglog(x, [f(r) for r in x], ls, lw=1.2 if name != "YTM (29)" else 0.8, label=name)
    ax.loglog(ra, nu, "s", mfc="none", color="k", label="Elenbaas data (plot)")
    idx = a["numerical_idx"]
    ax.loglog(ra[idx], a["numerical"], "x", color="C3", label="numerical channel")
    ax.set_xlabel("Ra_b")
    ax.set_ylabel("Nu_b = h b / k")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_title("Nu_b against Ra_b", fontsize=9)
    ax = axs[1]
    for name, f in (("Elenbaas (8)", ch.nu_elenbaas), ("Bar-Cohen-Rohsenow (21)", ch.nu_bcr), ("Raithby-Hollands (22)", ch.nu_rh), ("Churchill (20)", ch.nu_churchill)):
        ax.semilogx(ra, [100 * (f(r) / n - 1) for r, n in zip(ra, nu)], "o-", ms=3, lw=0.8, label=name)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Ra_b")
    ax.set_ylabel("correlation / data - 1 (%)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_title("difference from the plotted points (about +-8 % of reading)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_elenbaas_data_against_correlations.png", dpi=105)
    plt.close(fig)


def fig_03(res):
    """!
    @brief The array coefficient h_a of the 100 x 100 mm array of Bar-Cohen, Iyengar and Kraus against the spacing, for three ambient temperatures, with the published values.
    @param res Loaded JSON (unused, the curves are recomputed).
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.2))
    s = np.linspace(2e-3, 15e-3, 80)
    ax = axs[0]
    for amb, c in ((20.0, "C0"), (25.0, "C1"), (45.0, "C2")):
        ax.plot(s * 1e3, [S.bik_array(25.0, v, 1e-3, 0.045, 0.1, 0.1, 200.0, amb)["ha"] for v in s], color=c, label="ambient %d degC" % amb)
    ax.plot([8.0], [52.4], "k*", ms=11, label="paper: 52.4 near 8 mm (plot text)")
    ax.set_xlabel("fin spacing s (mm)")
    ax.set_ylabel("h_a (W/m2K)")
    ax.set_title("t = 1 mm, H = 45 mm, k = 200, theta_b = 25 K", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax = axs[1]
    ss = np.linspace(4e-3, 15e-3, 40)
    for amb, c in ((20.0, "C0"), (45.0, "C2")):
        ax.plot(ss * 1e3, [S.bik_least_material(25.0, v, 0.1, 0.1, 200.0, amb)["ha"] for v in ss], color=c, label="least material (t = s), ambient %d" % amb)
    ax.plot([9.0], [198.0], "k*", ms=11, label="paper: 198 at s = t = 9 mm")
    ax.set_xlabel("s = t (mm)")
    ax.set_ylabel("h_a (W/m2K)")
    ax.set_title("least-material fins (equation 20)", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_bik_array_reproduction.png", dpi=105)
    plt.close(fig)


def fig_04(res):
    """!
    @brief The Prandtl function of the isothermal vertical plate: the similarity solution (Ostrach 1953, independent solver), the table of the report and the Churchill and Chu term.
    @param res Loaded JSON.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.0))
    pr = np.logspace(-2, 3, 40)
    ax = axs[0]
    ax.semilogx(pr, [S.churchill_prandtl_function(p) for p in pr], "-", label="Churchill and Chu: 0.670 / [1 + (0.492/Pr)^(9/16)]^(4/9)")
    rows = res["C"]
    ax.semilogx([r["pr"] for r in rows], [r["f_ostrach"] for r in rows], "o", label="similarity solution (this study)")
    ax.semilogx([r["pr"] for r in rows], [(4.0 / 3.0) * r["table"] / np.sqrt(2.0) / r["pr"] ** 0.25 for r in rows], "x", color="k", label="Ostrach Table I (read)")
    ax.set_xlabel("Pr")
    ax.set_ylabel("Nu_L / Ra_L^(1/4)")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)
    ax = axs[1]
    ax.semilogx([r["pr"] for r in rows], [100 * (r["f_churchill"] / r["f_ostrach"] - 1) for r in rows], "o-")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Pr")
    ax.set_ylabel("Churchill-Chu term / similarity - 1 (%)")
    ax.grid(True, alpha=0.3)
    ax.set_title("0.5 % or less over five decades of Pr", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_vertical_plate_prandtl_function.png", dpi=105)
    plt.close(fig)


def fig_05(res):
    """!
    @brief Measured mean coefficient of six short horizontal arrays (plot values) against the program's uniform coefficient, the channel fraction of Proposal B and Tari and Mehrtash's equation 5.
    @param res Loaded JSON.
    @return None.
    """
    d = res["D"]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)
    for ax, (gap, keys) in zip(axs, ((5.55, ("4", "5", "6")), (14.35, ("1", "2", "3")))):
        for k, c in zip(keys, ("C0", "C1", "C2")):
            rows = d[k]
            dt = [r["dt"] for r in rows]
            ax.plot(dt, [r["h_meas"] for r in rows], "o-", color=c, label="array %s measured" % k)
            ax.plot(dt, [r["h_uniform"] for r in rows], "--", color=c, lw=0.9)
            ax.plot(dt, [r["h_phi_L"] for r in rows], ":", color=c, lw=1.1)
        ax.plot([], [], "k--", lw=0.9, label="program: uniform h")
        ax.plot([], [], "k:", lw=1.1, label="uniform h x phi (L = 100 mm)")
        ax.set_title("gap %.2f mm" % gap, fontsize=9)
        ax.set_xlabel("base excess (K)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    axs[0].set_ylabel("mean coefficient on the total area (W/m2K)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_horizontal_arrays_measured.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    with open(DATA) as f:
        results = json.load(f)
    fig_02(results)
    fig_03(results)
    fig_04(results)
    fig_05(results)
    print("figures written to", OUT)
