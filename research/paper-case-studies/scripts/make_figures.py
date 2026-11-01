#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@note figures 07 (convergence of the 3D reference) and 08 (vertical plate) were added after the runs.
@brief Data figures of research/paper-case-studies. Figure 04 needs no study run (the plotted markers of Soleymani Koohbanani's Fig. 33 and equations 28 and 29); the figures of the results
       (05 onward) are listed in the README and are drawn from out/*.json once the studies have been run (this script then fails with a clear message, it does not invent data).
@details Files: fig_04_fig33_markers_against_eq28.png (always); fig_05_via_models_against_reference.png and fig_06_laminate_error_map.png (only when out/study_measured_vias.json and
         out/study_thick_laminate.json exist).
         Usage: .venv/bin/python research/paper-case-studies/scripts/make_figures.py   (from the repository root).
"""

import json
import sys

import _bootstrap
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

import axisym_cell as AC                 # noqa: E402
import measured_data as MD               # noqa: E402


def fig_04():
    """!
    @brief The four measured markers of Fig. 33 (plot) against equations 28 and 29 evaluated for the samples of Table 9.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for kind, color, fn in (("straight", "tab:blue", AC.k_overall_straight), ("staggered", "tab:green", AC.k_overall_staggered)):
        xs = np.linspace(0.8, 3.0, 60)
        ax.plot(xs, [fn(x * 1e-3, 0.65e-3, 0.61e-3) for x in xs], color=color, lw=1.2, label=f"eq. {28 if kind == 'straight' else 29}, D_o 0.65 / D_i 0.61 mm")
    for g, (kind, side, samples, x) in MD.ARRANGEMENTS.items():
        fn = AC.k_overall_straight if kind == "straight" else AC.k_overall_staggered
        vals = [fn(side * 1e-3, MD.TABLE_9[s][3] * 1e-3, MD.TABLE_9[s][2] * 1e-3) for s in samples]
        ax.plot([x] * len(vals), vals, "_", color="k", ms=12, mew=1.4)
        km, lo, hi = MD.FIG33_MEASURED[g]
        ax.errorbar([x], [km], yerr=None if lo is None else [[km - lo], [hi - km]], fmt="s" if kind == "straight" else "D", color="tab:red", capsize=3)
    ax.plot([], [], "_", color="k", ms=12, mew=1.4, label="eq. 28/29 for each sample of the group")
    ax.plot([], [], "s", color="tab:red", label="measured (read from the plot, +-0.2)")
    ax.set_xlabel("spacing between vias (mm)")
    ax.set_ylabel("through-plane conductivity (W/mK)")
    ax.legend(fontsize=7)
    ax.set_title("Fig. 33 of the thesis: four measured markers, nine samples", fontsize=9)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_04_fig33_markers_against_eq28.png", dpi=105)
    plt.close(fig)


def fig_results():
    """!
    @brief The result figures, from the json files of the studies; refuses when they do not exist.
    @return None.
    @throws SystemExit If the studies have not been run.
    """
    needed = [_bootstrap.OUT / "study_measured_vias.json", _bootstrap.OUT / "study_thick_laminate.json"]
    missing = [p.name for p in needed if not p.exists()]
    if missing:
        raise SystemExit("result figures wait for the runs: missing out/" + ", out/".join(missing))
    via = json.load(open(needed[0]))
    lam = json.load(open(needed[1]))
    # Figure 05: error of every model against the solver with the same boundary condition, per sample
    rows = via["C"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for m in sorted({r["model"] for r in rows}):
        sel = [r for r in rows if r["model"] == m and r["grid_mm"] == min(x["grid_mm"] for x in rows if x["model"] == m and x["sample"] == r["sample"])]
        ax.plot([r["sample"] for r in sel], [r["err"] * 100 for r in sel], "o-", label=m)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("sample (Table 9)")
    ax.set_ylabel("resistance error against the unit-cell solver (%)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_05_via_models_against_reference.png", dpi=105)
    plt.close(fig)
    # Figure 06: error of the FVM at 0.25 mm for each option pair of the laminate rule, against the extrapolated 3D reference, per (S, t) at h = 1e3 (FR-4 0.9, 0.3), bare and pad boards
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), sharey=True)
    pairs = ((0.4, 4), (0.8, 2), (0.2, 8), (0.1, 16))
    cases = [(s_, t_) for s_ in (2, 5, 10) for t_ in (0.8, 1.6, 3.2)]
    for ax, kind in zip(axes, ("bare", "pad")):
        for k, (sm, nm) in enumerate(pairs):
            vals = []
            for s_, t_ in cases:
                v = [r["err_pct"] for r in lam[kind] if r["model"] == "fvm" and r["cell"] == 0.25 and (r["s_max"], r["n_max"]) == (sm, nm) and r["S"] == s_ and r["t"] == t_ and r["h"] == 1e3 and r["kxy"] == 0.9]
                vals.append(v[0] if v else np.nan)
            ax.bar(np.arange(len(cases)) + (k - 1.5) * 0.2, vals, 0.2, label=f"s_max {sm}, n_max {nm}" + (" (default)" if (sm, nm) == (0.4, 4) else ""))
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels([f"{s_}\n{t_}" for s_, t_ in cases], fontsize=7)
        ax.set_xlabel("source S (mm) and thickness t (mm)")
        ax.set_title(f"{kind} board, h = 1e3 (a missing bar was refused by the memory guard)", fontsize=8)
    axes[0].set_ylabel("R' error of the FVM at 0.25 mm against the 3D reference (%)")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_06_laminate_error_map.png", dpi=105)
    plt.close(fig)


def fig_s2_convergence():
    """!
    @brief Figure 07: the convergence of the 3D reference against the pixel and the sub-slab count (S = 2 mm, h = 1e6), with equation 50 and the extrapolation; solves the small grids of the study (about 1 minute).
    @return None.
    """
    import study_thick_laminate as S2
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    for ax, t in zip(axes, (1.6, 3.2)):
        c = {"S": 2.0, "W": 20.0, "t": t, "kxy": 0.9, "kz": 0.3, "h": 1.0e6}
        rp = S2.closed_form(c)[2]
        for px in (6, 8, 12, 16):
            nss = [ns for ns in (4, 8, 16, 32, 64) if 25 * px * px * (ns + 2) <= 130000]
            ax.plot(nss, [(S2.reference_3d(c, px_div=px, n_sub=ns) / rp - 1) * 100 for ns in nss], "o-", label=f"pixel S/{px}")
        ax.axhline(0, color="k", lw=1.0)
        ax.axhline((S2.reference_3d_extrap(c) / rp - 1) * 100, color="tab:red", ls="--", lw=1.0, label="extrapolated")
        ax.set_xscale("log", base=2)
        ax.set_yscale("symlog", linthresh=1.0)
        ax.set_xlabel("sub-slabs of the laminate")
        ax.set_ylabel("3D reference against equation 50 (% of R')")
        ax.set_title(f"S = 2 mm on 20 mm, t = {t} mm, h = 1e6", fontsize=8)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_07_reference_convergence.png", dpi=105)
    plt.close(fig)


def fig_s3_plate():
    """!
    @brief Figure 08: the wall temperature of the vertical plate of Lee and Yovanovich: the independent conjugate solver, the values read from the paper's curves (plot), Zinnes' thermocouples (plot) and the strip means of the program's FVM (computed coefficients) from out/study_vertical_plate.json.
    @return None.
    """
    import study_vertical_plate as S3
    path = _bootstrap.OUT / "study_vertical_plate.json"
    if not path.exists():
        raise SystemExit("figure 08 waits for out/study_vertical_plate.json")
    res = json.load(open(path))
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.2))
    for ax, name in zip(axes, ("glass", "ceramic")):
        ks, eps_p = S3.CASES[name]
        for eps, ls in ((0.0, "--"), (eps_p, "-")):
            r = S3.conjugate(name, eps)
            ax.plot(r["z"] / (S3.L_MM * 1e-3), r["rise"], ls, label=f"independent solver, eps {eps}")
            ref = S3.PLOT_MODEL[(name, eps)]
            ax.plot([0.27, 0.77, 0.52, 0.0], [ref[0], ref[1], ref[2], ref[3]], "o", ms=4, color="k" if eps else "grey", mfc="none", label="paper's curve (plot)" if eps else None)
        zz, vv = zip(*S3.ZINNES[name])
        ax.plot(zz, vv, "^", color="tab:red", label="Zinnes thermocouples (plot)")
        rows = [x for x in res["P"] if x["plate"] == name and x["model"] == "fvm" and x["cell"] == 0.254 and x["form"] == "general"]
        if rows:
            ax.axhline(rows[0]["mean1"], color="tab:green", lw=1.2, label="program FVM, computed h (strip mean)")
        ax.set_xlabel("z / L (leading edge at 0)")
        ax.set_ylabel("wall temperature above ambient (K)")
        ax.set_title(f"{name} plate, k_s {ks} W/mK", fontsize=9)
        ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_08_vertical_plate_conjugate.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw figure 04 and, when the runs exist, the result figures.
    @return int Exit code.
    """
    _bootstrap.FIGURES.mkdir(exist_ok=True)
    fig_04()
    for fn in (fig_results, fig_s2_convergence, fig_s3_plate):
        try:
            fn()
        except SystemExit as exc:
            print(exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
