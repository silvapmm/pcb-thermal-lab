#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures of the investigation (numbers 06 to 16), drawn from the JSON files that the study scripts leave in out/; a figure whose file is missing is skipped with a message.
@details One numbering with make_diagrams.py (figures 01 to 05 are the drawings). Each figure quotes only numbers that the README prints from the same files.
         06 error against n per stack-up with the 1/n line; 07 window width and gap sweeps; 08 real windows (bars and the fields of the first window); 09 error against unknowns for the laws of n;
         10 the validation rows before and after; 11 the FDM; 12 the step response; 13 the SOR sweeps; 14 the face-term variants; 15 the mask variants; 16 the four treatments and the rule.
         Usage: .venv/bin/python research/laminate-nodes/scripts/make_figures.py   (from the repository root, after the studies).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402
import numpy as np                                                           # noqa: E402

HERE = Path(__file__).resolve().parent.parent
OUT, FIG = HERE / "out", HERE / "figures"
NS = (1, 2, 3, 4, 6, 8)


def val(x):
    """!
    @brief The number inside a (format, value) pair saved as a list, or the number itself.
    @param x A number, or [format, number].
    @return float (or the input when it is not a number).
    """
    return x[1] if isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) else x


def load(name):
    """!
    @brief A JSON file of out/, or None with a message.
    @param name File stem.
    @return Parsed object or None.
    """
    f = OUT / f"{name}.json"
    if not f.exists():
        print(f"skipped (no {f.name})")
        return None
    return json.loads(f.read_text())


def finish(fig, name):
    """!
    @brief Tighten and save a figure into figures/.
    @param fig Figure.
    @param name File name.
    @return None.
    """
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=105)
    plt.close(fig)
    print("wrote", name)


def fig06():
    """!
    @brief Error against n per board, equal and graded sub-gaps, with the fitted 1/n line.
    @return None.
    """
    rows = load("n_law_A")
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    n = np.linspace(1, 8, 100)
    for ax, key in zip(axs, ("r1", "r2")):
        for r in rows:
            ax.plot(NS, r[key], marker="o", markersize=3, linewidth=1, label=r["board"])
            f = r["fit " + key]
            ax.plot(n[n >= 2], f["e_inf"] + f["a"] / n[n >= 2], color="grey", linewidth=0.5, linestyle=":")
        ax.axhline(0, color="k", linewidth=0.5)
        ax.set_xlabel("sub-gaps n")
        ax.set_title("equal sub-gaps" if key == "r1" else "graded 2:1", fontsize=9)
    axs[0].set_ylabel("error of the peak, % of the reference")
    axs[0].legend(fontsize=5, ncol=2)
    finish(fig, "fig_06_error_against_n.png")


def fig07():
    """!
    @brief Windows narrower than the gap: error against the window width over the gap, for n = 1, the law and n = 8.
    @return None.
    """
    rows = load("narrow_window")
    if not rows:
        return
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
    for ax, key in zip(axs, ("n=1", "law", "n=8 vs same-cell 3D")):
        for d in sorted({r["gap mm"] for r in rows}):
            sel = sorted([r for r in rows if r["gap mm"] == d and r["cell"] == 0.5], key=lambda r: r["w mm"])
            ax.plot([val(r["w/d"]) for r in sel], [r[key] for r in sel], marker="o", markersize=3, label=f"d = {d} mm")
        ax.set_xscale("log")
        ax.axhline(0, color="k", linewidth=0.5)
        ax.set_xlabel("window width / gap")
        ax.set_title(key, fontsize=9)
    axs[0].set_ylabel("error of the peak, %")
    axs[0].legend(fontsize=6)
    finish(fig, "fig_07_narrow_windows.png")


def fig08():
    """!
    @brief Real windows: error of the mean heater rise of the program and of the rule, and the fields of the first window.
    @return None.
    """
    files = sorted(OUT.glob("windows_real_*.json"))
    if not files:
        print("skipped (no windows_real json)")
        return
    rows = json.loads(files[0].read_text())
    fig, axs = plt.subplots(1, 4 if (OUT / "windows_real_fields.npz").exists() else 1, figsize=(13, 3.6))
    axs = np.atleast_1d(axs)
    x = np.arange(len(rows))
    for off, key in ((-0.27, "program (2 nodes) mean %"), (0.0, "n=8 all mean %"), (0.27, "proposed mean %")):
        axs[0].bar(x + off, [r[key] for r in rows], width=0.27, label=key.replace(" mean %", ""))
    axs[0].set_xticks(x)
    axs[0].set_xticklabels([r["window"].split(" ")[0] for r in rows], fontsize=6, rotation=30)
    axs[0].set_ylabel("error of the mean heater rise, %")
    axs[0].legend(fontsize=6)
    if len(axs) == 4:
        d = np.load(OUT / "windows_real_fields.npz")
        vmax = float(np.nanmax(d["ref_surf"]))
        for ax, (a, t) in zip(axs[1:], ((d["fill"], "copper fill of the cell"), (d["ref_surf"], "reference face rise (K)"), (d["rule_top"], "rule, top node rise (K)"))):
            im = ax.imshow(a, origin="lower", vmax=None if "fill" in t else vmax)
            ax.set_title(t, fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, fraction=0.046)
    finish(fig, "fig_08_real_windows.png")


def fig09():
    """!
    @brief The laws of n on the error-cost plane (mean absolute error against the mean ragged unknown ratio).
    @return None.
    """
    rows = load("n_law_B")
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for n_max in sorted({r["n_max"] for r in rows}):
        sel = [r for r in rows if r["n_max"] == n_max]
        ax.plot([val(r["mean unk x"]) for r in sel], [val(r["mean |e| %"]) for r in sel], marker="o", label=f"n_max = {n_max}")
        for r in sel:
            ax.annotate(f"{val(r['s_max mm'])}", (val(r["mean unk x"]), val(r["mean |e| %"])), fontsize=5)
    ax.set_xlabel("unknowns, ragged, times the program's (mean over the boards)")
    ax.set_ylabel("mean absolute error, %")
    ax.set_title("laws n = min(n_max, ceil(d / s_max)); labels: s_max in mm", fontsize=8)
    ax.legend(fontsize=7)
    finish(fig, "fig_09_error_against_unknowns.png")


def fig10():
    """!
    @brief The validation scenarios: change of the FVM peak with the rule, in K.
    @return None.
    """
    rows = load("validation_rows")
    if not rows:
        return
    rows = [r for r in rows if "FVM change K" in r]
    fig, ax = plt.subplots(figsize=(9, 0.25 * len(rows) + 1.5))
    ax.barh(range(len(rows)), [val(r["FVM change K"]) for r in rows])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["board"][:48] for r in rows], fontsize=5)
    ax.invert_yaxis()
    ax.set_xlabel("change of the FVM peak with the rule, K (1 mm cell)")
    finish(fig, "fig_10_validation_rows.png")


def fig11():
    """!
    @brief The FDM with the construction against the program's FDM and the FVM with the rule.
    @return None.
    """
    rows = load("fdm")
    if not rows:
        return
    rows = [r for r in rows if r["cell"] == 0.5]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(rows))
    for off, key in ((-0.3, "FDM program"), (-0.1, "FDM rule"), (0.1, "FVM program"), (0.3, "FVM rule")):
        ax.bar(x + off, [r[key] for r in rows], width=0.2, label=key)
    ax.set_xticks(x)
    ax.set_xticklabels([r["board"] for r in rows], fontsize=5, rotation=40, ha="right")
    ax.set_ylabel("error of the peak, %")
    ax.legend(fontsize=6)
    finish(fig, "fig_11_fdm.png")


def fig12():
    """!
    @brief Step response of the hottest point: reference and layered models.
    @return None.
    """
    d = load("transient")
    if not d:
        return
    fig, axs = plt.subplots(1, len(d["curves"]), figsize=(11, 3.5))
    for ax, (name, c) in zip(np.atleast_1d(axs), d["curves"].items()):
        for k in ("program", "fvm rule", "fdm rule", "ref3d"):
            ax.semilogx(c["t"], c[k], marker="o", markersize=2, label=k, linestyle="-" if k != "ref3d" else "--")
        ax.set_title(name, fontsize=8)
        ax.set_xlabel("t, s")
    np.atleast_1d(axs)[0].set_ylabel("peak rise, K")
    np.atleast_1d(axs)[0].legend(fontsize=6)
    finish(fig, "fig_12_step_response.png")


def fig13():
    """!
    @brief SOR sweeps on the program's network and on the ladder.
    @return None.
    """
    d = load("cost_sor")
    if not d:
        return
    rows = d["sor"]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.barh(range(len(rows)), [r["iterations"] for r in rows])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r['board'][:18]} | {r['case']}" for r in rows], fontsize=6)
    ax.invert_yaxis()
    ax.set_xlabel("sweeps to a residual of 1e-8")
    finish(fig, "fig_13_sor_sweeps.png")


def fig14():
    """!
    @brief The face-term variants on the windows of part A.
    @return None.
    """
    d = load("vertical_face")
    if not d:
        return
    rows = d["A windows peak"]
    keys = ["off", "vert only", "vert + p=0", "vert + p=1", "vert + p=2"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(rows))
    for i, k in enumerate(keys):
        ax.bar(x + (i - 2) * 0.16, [r[k] for r in rows], width=0.16, label=k)
    ax.set_xticks(x)
    ax.set_xticklabels([r["board"] for r in rows], fontsize=5, rotation=40, ha="right")
    ax.set_ylabel("error of the peak, % (n = 1)")
    ax.legend(fontsize=6)
    finish(fig, "fig_14_vertical_and_face.png")


def fig15():
    """!
    @brief The mask variants on the error-cost plane.
    @return None.
    """
    rows = load("mask")
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for r in rows:
        ax.scatter(val(r["ragged x"]), val(r["mean |e| %"]))
        ax.annotate(r["variant"], (val(r["ragged x"]), val(r["mean |e| %"])), fontsize=5)
    ax.set_xlabel("unknowns, ragged, times the program's")
    ax.set_ylabel("mean absolute error, %")
    finish(fig, "fig_15_mask_variants.png")


def fig16():
    """!
    @brief The four old treatments and the rule on the simple boards.
    @return None.
    """
    rows = load("s0_four_treatments")
    if not rows:
        return
    keys = [k for k in rows[0] if k not in ("board", "ref K", "unk x")]
    fig, ax = plt.subplots(figsize=(11, 4))
    x = np.arange(len(rows))
    w = 0.8 / len(keys)
    for i, k in enumerate(keys):
        ax.bar(x + (i - len(keys) / 2) * w, [r[k] for r in rows], width=w, label=k[:34])
    ax.set_xticks(x)
    ax.set_xticklabels([r["board"] for r in rows], fontsize=5, rotation=45, ha="right")
    ax.set_ylabel("error of the peak, %")
    ax.legend(fontsize=5)
    finish(fig, "fig_16_four_treatments_and_the_rule.png")


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    for f in (fig06, fig07, fig08, fig09, fig10, fig11, fig12, fig13, fig14, fig15, fig16):
        f()
