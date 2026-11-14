#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the results of the finite-element extensions (fig_05 on), drawn from the caches `out/s1.json` to `out/s5.json` that the study scripts write.
@details Run from the repository root with the scratch environment (needs matplotlib): `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/make_figures.py`.
         Every number drawn is a number printed by a study script (the caches hold them); nothing is typed here.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
import numpy as np                                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "figures")
DATA = os.path.join(HERE, "..", "out")


def cache(n):
    """!
    @brief Read a cache.
    @param n Number of the study cache (s<n>.json).
    @return dict (empty when absent).
    """
    p = os.path.join(DATA, f"s{n}.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def fig_hollow():
    """!
    @brief Figure 5: study 1, the finite-element via effect by core and mesh, and the program's error against it.
    @return None.
    """
    r = cache(1)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for d, h, ls in ((0.16, 200.0, "-"), (3.0, 200.0, "--"), (0.16, 1000.0, "-."), (3.0, 1000.0, ":")):
        for core, c in (("open", "#2c7fb8"), ("resin", "#7fcdbb"), ("copper", "#d95f0e")):
            hs = [hf for hf in (0.2, 0.1, 0.05) if f"1a|{d}|{h}|{hf}|{core}|" in r]
            ax[0].plot(hs, [r[f"1a|{d}|{h}|{hf}|{core}|"]["E"] for hf in hs], ls, color=c, marker="o", ms=3, label=f"{core} d{d} h{int(h)}" if h == 200.0 else None)
    ax[0].set_xscale("log")
    ax[0].invert_xaxis()
    ax[0].set_xlabel("plan size hf (mm)")
    ax[0].set_ylabel("finite-element via effect E (K)")
    ax[0].set_title("FEM E by core and mesh", fontsize=9)
    ax[0].legend(fontsize=6)
    for k, (d, h) in enumerate(((0.16, 200.0), (0.16, 1000.0))):
        a = ax[1 + k]
        ref = r.get(f"1a|{d}|{h}|0.05|open|", {}).get("E")
        if ref is None:
            continue
        for model, n, c, lab in (("fvm", None, "#1b9e77", "FVM default"), ("fvm", 8, "#66a61e", "FVM 8 sub-gaps"), ("fdm", None, "#d95f02", "FDM")):
            cells = [cl for cl in (1.0, 0.5, 0.25) if f"P1a|{d}|{h}|{cl}|{model}|{n}|open" in r]
            a.plot(cells, [100 * ((r[f"P1a|{d}|{h}|{cl}|{model}|{n}|base"] - r[f"P1a|{d}|{h}|{cl}|{model}|{n}|open"]) / ref - 1) for cl in cells], marker="o", color=c, label=lab)
        a.axhline(0, color="k", lw=0.6)
        a.set_xscale("log")
        a.invert_xaxis()
        a.set_xlabel("cell (mm)")
        a.set_ylabel("error of E, open barrel (%)")
        a.set_title(f"program vs FEM, via {d} mm from the wall, h_side {int(h)}", fontsize=8)
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_05_hollow_barrel_results.png"), dpi=140)
    plt.close(fig)


def fig_cluster():
    """!
    @brief Figure 6: study 2, the finite-element part temperature by mesh (A and B) and the program's error against variant A.
    @return None.
    """
    r = cache(2)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for var, c in (("A", "#2c7fb8"), ("B", "#d95f0e")):
        hs = [hf for hf in (0.4, 0.2, 0.1) if f"{var}|6.0|{hf}|full" in r]
        ax[0].plot(hs, [r[f"{var}|6.0|{hf}|full"]["part_mean"] for hf in hs], marker="o", color=c, label=f"variant {var}")
    ax[0].set_xscale("log")
    ax[0].invert_xaxis()
    ax[0].set_xlabel("plan size hf (mm)")
    ax[0].set_ylabel("part mean rise (K)")
    ax[0].set_title("FEM, 6 x 6 mm part", fontsize=9)
    ax[0].legend()
    ref = r.get("A|6.0|0.1|full", {}).get("part_mean")
    for model, c in (("fvm", "#1b9e77"), ("fdm", "#d95f02"), ("solid3d", "#7570b3"), ("lumped", "#e7298a"), ("analytic", "#66a61e")):
        cells = [cl for cl in (1.0, 0.5, 0.25) if f"P|6|full|{model}|{cl}" in r and "error" not in r[f"P|6|full|{model}|{cl}"]]
        if ref and cells:
            ax[1].plot(cells, [100 * (r[f"P|6|full|{model}|{cl}"]["part_mean"] / ref - 1) for cl in cells], marker="o", color=c, label=model)
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_xscale("log")
    ax[1].invert_xaxis()
    ax[1].set_xlabel("cell (mm)")
    ax[1].set_ylabel("error of the part mean rise (%)")
    ax[1].set_title("program vs FEM variant A", fontsize=9)
    ax[1].legend(fontsize=7)
    e = r.get("A|6.0|0.1|full|novia", {}).get("part_mean")
    if e and ref:
        efem = e - ref
        for model, c in (("fvm", "#1b9e77"), ("fdm", "#d95f02"), ("solid3d", "#7570b3"), ("lumped", "#e7298a"), ("analytic", "#66a61e")):
            cells = [cl for cl in (1.0, 0.5, 0.25) if f"P|6|full|{model}|{cl}|novia" in r and f"P|6|full|{model}|{cl}" in r and "error" not in r[f"P|6|full|{model}|{cl}"]]
            if cells:
                ax[2].plot(cells, [100 * ((r[f"P|6|full|{model}|{cl}|novia"]["part_mean"] - r[f"P|6|full|{model}|{cl}"]["part_mean"]) / efem - 1) for cl in cells], marker="o", color=c, label=model)
        ax[2].axhline(0, color="k", lw=0.6)
        ax[2].set_xscale("log")
        ax[2].invert_xaxis()
        ax[2].set_xlabel("cell (mm)")
        ax[2].set_ylabel("error of the via effect E (%)")
        ax[2].set_title(f"via effect (FEM {efem:.3f} K)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_06_cluster_results.png"), dpi=140)
    plt.close(fig)


def fig_transient():
    """!
    @brief Figure 7: study 5, the disc check against the axisymmetric reference and the plate wave swing by mesh.
    @return None.
    """
    r = cache(5)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for tag, c in (("disc|12|24|cons", "#2c7fb8"), ("disc|18|24|cons", "#d95f0e")):
        if tag in r:
            st = np.array(r[tag]["step"])
            ax[0].semilogx(st[:, 0], 100 * (st[:, 1] / st[:, 2] - 1), marker="o", color=c, label=f"{tag} ({r[tag]['n']} unknowns)")
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("FEM / axisymmetric reference - 1 (%)")
    ax[0].set_title("disc board, step response (footprint mean)", fontsize=9)
    ax[0].legend(fontsize=7)
    for name, c in (("centre", "#2c7fb8"), ("mean", "#d95f0e")):
        hs = [(hf, r[f"fast|{hf}|24"][name]) for hf in (0.4, 0.2, 0.1) if f"fast|{hf}|24" in r]
        if hs:
            ax[1].plot([h for h, _ in hs], [v for _, v in hs], marker="o", color=c, label=f"FEM {name}")
    pf = r.get("prog_fast", {})
    if pf:
        ax[1].axhline(pf["floor"], color="g", ls="--", label="program closed form (eq. 10.5)")
        ax[1].axhline(pf.get("fvm1.0", {}).get("node_swing", np.nan), color="r", ls=":", label="program node swing (1 mm)")
    ax[1].set_xscale("log")
    ax[1].invert_xaxis()
    ax[1].set_xlabel("plan size hf (mm)")
    ax[1].set_ylabel("swing of 1 W, 20 Hz, 30 % (K)")
    ax[1].set_title("60 x 40 mm plate, 10 mm part", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_07_transient_results.png"), dpi=140)
    plt.close(fig)


def fig_stripes_l():
    """!
    @brief Figure 8: studies 3 and 4, the program's heater-mean error against the finest finite-element value on the stripes board and the L boards.
    @return None.
    """
    r3, r4 = cache(3), cache(4)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for kind, c in (("stripes", "#d95f0e"), ("plain", "#2c7fb8")):
        vals = [r3[f"{kind}|{hf}"]["heater_mean"] for hf in (0.4, 0.2, 0.1) if f"{kind}|{hf}" in r3]
        if not vals:
            continue
        for model, ls in (("fvm", "-"), ("fdm", "--")):
            cells = [cl for cl in (1.0, 0.5, 0.25) if f"P|{kind}|{cl}|{model}" in r3]
            ax[0].plot(cells, [100 * ((r3[f"P|{kind}|{cl}|{model}"].get("heater_mean_weights", r3[f"P|{kind}|{cl}|{model}"]["heater_mean"]) if model == "fvm" else r3[f"P|{kind}|{cl}|{model}"]["heater_mean"]) / vals[-1] - 1) for cl in cells],
                       ls, marker="o", color=c, label=f"{kind} {model}")
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xscale("log")
    ax[0].invert_xaxis()
    ax[0].set_xlabel("cell (mm)")
    ax[0].set_ylabel("heater mean error vs FEM (%)")
    ax[0].set_title("stripes board and control, 200 W/m2K", fontsize=9)
    ax[0].legend(fontsize=7)
    for kind, c in (("wall", "#d95f0e"), ("in", "#2c7fb8")):
        vals = [r4[f"{kind}|{hf}"]["heater_mean"] for hf in (0.4, 0.2, 0.1) if f"{kind}|{hf}" in r4]
        if not vals:
            continue
        for model, ls in (("fvm", "-"), ("fdm", "--")):
            cells = [cl for cl in (1.0, 0.5, 0.25) if f"P|{kind}|{cl}|{model}" in r4]
            ax[1].plot(cells, [100 * ((r4[f"P|{kind}|{cl}|{model}"].get("heater_mean_weights", r4[f"P|{kind}|{cl}|{model}"]["heater_mean"]) if model == "fvm" else r4[f"P|{kind}|{cl}|{model}"]["heater_mean"]) / vals[-1] - 1) for cl in cells],
                       ls, marker="o", color=c, label=f"L {kind} {model}")
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_xscale("log")
    ax[1].invert_xaxis()
    ax[1].set_xlabel("cell (mm)")
    ax[1].set_title("L outline, 200 W/m2K", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_08_stripes_and_l_results.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    fig_hollow()
    fig_cluster()
    fig_transient()
    fig_stripes_l()
