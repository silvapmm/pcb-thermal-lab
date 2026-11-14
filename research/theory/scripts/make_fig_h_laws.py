#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_fig_h_laws.py
@brief Picture for `docs/theory.md` 8: the horizontal-face laws of the program against the laws printed in the sources, over the Rayleigh numbers of a PCB.

@details fig_48, left: the face turned up, area-mean Nu on L = A/P against Ra (Pr 0.71): the program (`convection.h_natural_horizontal`, 0.54 Ra^(1/4) up to 1e7,
         0.15 Ra^(1/3) above), Raithby-Hollands (Lienhard 2024 eq. 8.37a/b with the thick-layer correction, and eq. 8.35 above 1e7), Goldstein, Sparrow and Jones
         (Sc 2.5, 0.96 Ra^(1/6) below 200, 0.59 Ra^(1/4) above), the Goldstein-Lau numerical strip 0.621 Ra^(1/5) and Lewandowski's air data 0.766 Ra^(1/5)
         (all three printed by Yovanovich and Jafarpur 1993, pp 7 and 8), with the band of Ra of a 20 to 300 mm board at a 5 to 80 K rise.
         Middle: the same laws as the ratio program / law. Right: the face turned down: the program (0.475 Ra^(1/5)) against Fujii-Imura (Lienhard eq. 8.38, 0.58 on the
         width, 0.4396 on A/P), Kadambi-Drake (eq. 8.39 on a disc, 0.4655 on A/P), VDI 0.486, the Goldstein-Lau strip 0.524 and the old McAdams 0.27 Ra^(1/4).
         Closed forms only; the same numbers are in the table of `docs/theory.md` 8.
         Run: .venv/bin/python research/theory/scripts/make_fig_h_laws.py (from the repository root; a few seconds). Writes figures/fig_48_h_laws.png.
"""

import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parents[1] / "figures"
PR = 0.71                                                          # Prandtl number of air used for every law of the picture


def program_up(ra):
    """!
    @brief The program's face-up law (convection.h_natural_horizontal).
    @param ra Rayleigh number on A/P (scalar).
    @return Area-mean Nusselt number on A/P.
    """
    return 0.54 * ra ** 0.25 if ra <= 1e7 else 0.15 * ra ** (1.0 / 3.0)


def raithby_hollands(ra):
    """!
    @brief Lienhard 2024 eq. 8.37a with the thick-layer correction 8.37b (applied at every Ra, as in the audit), and eq. 8.35 above 1e7.
    @param ra Rayleigh number on A/P (scalar).
    @return Area-mean Nusselt number on A/P.
    """
    if ra > 1e7:
        return 0.14 * ra ** (1.0 / 3.0) * (1.0 + 0.0107 * PR) / (1.0 + 0.01 * PR)
    nu = 0.560 * ra ** 0.25 / (1.0 + (0.492 / PR) ** (9.0 / 16.0)) ** (4.0 / 9.0)
    return 1.4 / math.log(1.0 + 1.4 / nu)


def gsj(ra):
    """!
    @brief Goldstein, Sparrow and Jones (mass transfer, Sc 2.5) as printed by Yovanovich and Jafarpur (1993) eqs. 15 and 16.
    @param ra Rayleigh number on A/P (scalar).
    @return Area-mean Nusselt number on A/P.
    """
    return 0.96 * ra ** (1.0 / 6.0) if ra < 200 else 0.59 * ra ** 0.25


def main():
    """!
    @brief Draw fig_48 and write it to research/theory/figures.
    @return None.
    """
    ra = np.logspace(1.5, 7.5, 300)
    up = {"program 0.54 Ra^1/4 (0.15 Ra^1/3 > 1e7)": [program_up(r) for r in ra],
          "Raithby-Hollands, Lienhard 8.37 (8.35 > 1e7)": [raithby_hollands(r) for r in ra],
          "Goldstein-Sparrow-Jones, Sc 2.5 (YJ eq. 15, 16)": [gsj(r) for r in ra],
          "Goldstein-Lau strip 0.621 Ra^1/5 (YJ p 7)": list(0.621 * ra ** 0.2),
          "Lewandowski, air 0.766 Ra^1/5 (YJ p 8)": list(0.766 * ra ** 0.2)}
    styles = ["k-", "C0--", "C1-.", "C2:", "C3--"]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    ax = axes[0]
    for (name, nu), st in zip(up.items(), styles):
        ax.loglog(ra, nu, st, label=name, lw=2 if st == "k-" else 1.4)
    for a in axes[:2]:
        a.axvspan(5.8e1, 1.8e6, color="0.9", zorder=0)
    ax.set_xlabel("Ra on L = A/P")
    ax.set_ylabel("Nu on A/P")
    ax.set_title("Face turned up (grey: boards 20 to 300 mm, 5 to 80 K)")
    ax.legend(fontsize=7, loc="upper left")
    ax = axes[1]
    prog = np.array(up["program 0.54 Ra^1/4 (0.15 Ra^1/3 > 1e7)"])
    for (name, nu), st in list(zip(up.items(), styles))[1:]:
        ax.semilogx(ra, 100.0 * (prog / np.array(nu) - 1.0), st, label=name)
    ax.axhline(0.0, color="k", lw=0.8)
    ax.set_xlabel("Ra on L = A/P")
    ax.set_ylabel("program / law − 1 (%)")
    ax.set_title("Face up: the program against each printed law")
    ax.set_ylim(-40, 80)
    ax.legend(fontsize=7, loc="upper left")
    ax = axes[2]
    down = {"program 0.475 Ra^1/5": 0.475, "Fujii-Imura on A/P 0.440 (8.38)": 0.58 * 8 ** 0.2 / 2,
            "Kadambi-Drake on A/P 0.466 (8.39)": 0.82 * 64 ** 0.2 * PR ** 0.034 / 4, "VDI 0.486": 0.486, "Goldstein-Lau strip 0.524": 0.524}
    for (name, c), st in zip(down.items(), styles):
        ax.loglog(ra, c * ra ** 0.2, st, label=name, lw=2 if st == "k-" else 1.4)
    ax.loglog(ra, 0.27 * ra ** 0.25, color="0.5", ls=":", label="McAdams 0.27 Ra^1/4 (used until 2.6.0)")
    ax.axvspan(5.8e1, 1.8e6, color="0.9", zorder=0)
    ax.set_xlabel("Ra on L = A/P")
    ax.set_ylabel("Nu on A/P")
    ax.set_title("Face turned down")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_48_h_laws.png", dpi=110)


if __name__ == "__main__":
    main()
