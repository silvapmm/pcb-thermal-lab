#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the investigation, drawn from the JSON files that the study scripts write to out/ (run the studies first).
@details fig_04 the laws against Ra as ratios to the program with the Ra range of the boards; fig_05 the cavity benchmark; fig_06 the plate in a cold box against the laws;
         fig_07 the change of the hottest rise of the 17 harness boards for each candidate pair. Missing input files are skipped with a message.
Usage: .venv/bin/python research/convection-laws/scripts/make_figures.py   (from the repository root)
"""

import json
import os
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import laws  # noqa: E402

OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"


def load(name):
    """!
    @brief Read a JSON result of the studies.
    @param name File name in out/.
    @return Parsed object or None.
    """
    p = OUT / name
    if not p.exists():
        print("missing", p)
        return None
    return json.loads(p.read_text())


def plate_rows():
    """!
    @brief The rows of the strip sweep from out/plate_mac.json and out/plate_mac_isolated.json, without repeats (same faces, Ra, box scale and resolution).
    @return list of dict.
    """
    seen, rows = set(), []
    for name in ("plate_mac.json", "plate_mac_isolated.json"):
        for r in load(name) or []:
            key = (r.get("faces", "both"), r["ra"], r["s"], r["fine"])
            if key not in seen:
                seen.add(key)
                rows.append(r)
    return rows


def fig04():
    """!
    @brief The laws as ratios to the program over Ra, with the Ra range of the boards of table 2.
    @return None.
    """
    ra = np.logspace(2, 8, 200)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    base_u, base_d = laws.C.program_up(ra), laws.C.program_down(ra)
    ax = axs[0]
    ax.semilogx(ra, laws.C.raithby_hollands_up(ra) / base_u, label="Raithby-Hollands (Lienhard 8.37, 1 < Ra < 1e7)")
    ax.semilogx(ra, laws.C.jaffer_up(ra) / base_u, label="Jaffer eq. 30 (fit of data)")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_title("Face up: candidate / program")
    ax = axs[1]
    for lab, f in (("0.475 Ra^1/5 (mean Goldstein-Lau, Yovanovich-Jafarpur p. 8)", laws.goldstein_lau_down), ("Fujii-Imura strip, W = 2 A/P", lambda r: laws.C.fujii_imura_down(r, 2.0)),
                   ("Fujii-Imura square, W = 4 A/P", lambda r: laws.C.fujii_imura_down(r, 4.0)), ("Kadambi-Drake disc", laws.C.kadambi_drake_down),
                   ("Jaffer eq. 56, square", lambda r: laws.C.jaffer_down_shape(r, 2.0))):
        ax.semilogx(ra, f(ra) / base_d, label=lab)
    ax.axhline(1, color="k", lw=0.8)
    ax.set_title("Face down: candidate / program")
    for ax in axs:
        ax.axvspan(3e2, 2e4, color="#f0d9a8", alpha=0.5, label="Ra of the boards (README 3.2)")
        ax.set_xlabel("Ra (L = A/P)")
        ax.set_ylim(0.4, 1.8)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=6.5, loc="upper right")
    axs[0].set_ylabel("Nu ratio")
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_laws_against_the_program_over_ra.png", dpi=105)
    plt.close(fig)


def fig05():
    """!
    @brief Cavity benchmark: error of the mean Nusselt number against the grid, and the Nu against Ra.
    @return None.
    """
    rows = load("cavity.json")
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    for ra in sorted({r["ra"] for r in rows}):
        sel = [r for r in rows if r["ra"] == ra and r["ratio"] == 1.0]
        axs[0].loglog([r["n"] for r in sel], [abs(r["error_pct"]) + 1e-3 for r in sel], "o-", label=f"Ra {ra:.0e}")
    axs[0].set_xlabel("cells per side (uniform grid)")
    axs[0].set_ylabel("|error| of Nu against de Vahl Davis, %")
    axs[0].legend()
    axs[0].grid(alpha=0.3, which="both")
    ref = {1e3: 1.118, 1e4: 2.243, 1e5: 4.519}
    best = {ra: [r for r in rows if r["ra"] == ra and r["ratio"] == 1.0][-1]["nu_hot"] for ra in ref}
    axs[1].loglog(list(ref), list(ref.values()), "ks", label="de Vahl Davis (1983), as remembered")
    axs[1].loglog(list(best), list(best.values()), "r.", ms=10, label="lib/mac2d.py, finest uniform grid")
    axs[1].set_xlabel("Ra")
    axs[1].set_ylabel("mean Nu of the hot wall")
    axs[1].legend()
    axs[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_cavity_benchmark_of_the_new_solver.png", dpi=105)
    plt.close(fig)


def fig06():
    """!
    @brief Nusselt numbers of the two faces of the strip in a cold box against the laws.
    @return None.
    """
    rows = plate_rows()
    if not rows:
        return
    ra = np.logspace(2.3, 4.2, 100)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
    for ax, face in zip(axs, ("up", "down")):
        for s, mk in ((1.0, "o"), (2.0, "s")):
            sel = [r for r in rows if r["s"] == s and r["fine"] == 1.0 and r.get("faces", "both") == "both"]
            ax.loglog([r["ra"] for r in sel], [r["nu_" + face] for r in sel], mk, label=f"cold box, s = {s:g}")
        iso = [r for r in rows if r.get("faces") == face and r["s"] == 1.0 and r["fine"] == 1.0]
        ax.loglog([r["ra"] for r in iso], [r["nu_" + face] for r in iso], "v", color="m", label="cold box s = 1, this face alone")
        gl = np.logspace(np.log10(40), np.log10(8e3), 20)
        ax.loglog(gl, (0.621 if face == "up" else 0.524) * gl ** 0.2, "k--", lw=1, label=f"Goldstein-Lau numerical strip {'0.621' if face == 'up' else '0.524'} Ra^1/5 (40 < Ra < 8e3, YJ p. 8)")
        if face == "up":
            ax.loglog(ra, laws.C.program_up(ra), label="program 0.54 Ra^1/4")
            ax.loglog(ra, laws.C.raithby_hollands_up(ra), label="Raithby-Hollands")
            ax.loglog([1e3, 1e4], [1.412, 2.075], "k^", label="open-domain solver (horizontal-plate-h, printed)")
        else:
            ax.loglog(ra, laws.C.program_down(ra), label="program 0.27 Ra^1/4")
            ax.loglog(ra, laws.goldstein_lau_down(ra), label="0.475 Ra^1/5")
            ax.loglog([1e3, 1e4], [2.296, 3.501], "k^", label="open-domain solver (horizontal-plate-h, printed)")
        ax.set_title(f"face {face} of a strip, both faces hot (L = A/P = half width)")
        ax.set_xlabel("Ra")
        ax.set_ylabel("Nu")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=6.5)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_strip_in_a_cold_box_against_the_laws.png", dpi=105)
    plt.close(fig)


def fig07():
    """!
    @brief Change of the hottest rise of the 17 harness boards for each candidate pair of laws (with radiation).
    @return None.
    """
    rows = load("board_effect.json")
    if not rows:
        return
    levels = ["RH+program-down", "RH+GL", "RH+FI", "Jaffer"]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    w = 0.2
    x = np.arange(len(rows))
    for k, lv in enumerate(levels):
        v = []
        for r in rows:
            a, b = r["rad|program"].get("rise"), r[f"rad|{lv}"].get("rise")
            v.append(100 * (b / a - 1) if a and b else np.nan)
        ax.bar(x + (k - 1.5) * w, v, w, label=lv)
    ax.set_xticks(x)
    ax.set_xticklabels([r["board"] for r in rows], rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("change of the hottest rise, %")
    ax.axhline(0, color="k", lw=0.8)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=7)
    ax.set_title("Computed h, FVM 2 mm, horizontal board: candidate pair against the program's laws")
    fig.tight_layout()
    fig.savefig(FIG / "fig_07_effect_on_the_harness_boards.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig04()
    fig05()
    fig06()
    fig07()
