"""!
@file study_channel_correlations.py
@brief Natural convection between vertical isothermal parallel plates: the Elenbaas correlation (1942) against the blended correlation of Raithby and Hollands, as quoted and analysed by Martin, Raithby and Yovanovich (1991), and the plate spacing that dissipates the most heat per unit of base area.
@details Both correlations are written there with the Nusselt number based on the half-width b of the channel and the Elenbaas Rayleigh number Ra* = Ra b / L:
         Elenbaas Nu = (Ra*/3) [1 - exp(-35 / (16 Ra*))]^(3/4); blended Nu = (Nu_fd^m + Nu_bl^m)^(1/m) with m = -1.9, Nu_fd = Ra*/3 (fully developed, small Ra*) and Nu_bl = 0.62 Ra*^(1/4)
         (boundary-layer limit). With the spacing S = 2b, Nu_S = 2 Nu_b and the Elenbaas number of the spacing is El = 16 Ra*, so that the fully developed limit reads Nu_S = El / 24 and the exponential
         of Elenbaas becomes exp(-35 / El). Heat per unit of base area of an array of thin plates at pitch S is proportional to Nu_S / S^2, and El grows as S^4, so the spacing that dissipates the
         most is the maximum of Nu_S / El^(1/2). The result is compared with the optimum of the composite correlation of Bar-Cohen and Rohsenow as quoted in the theory notes (not opened; the optimum is also quoted as El = 2.714^4 = 54.3) and with the practical
         value of about 50 of Simons. Run: .venv/bin/python research/effective-conductivity/scripts/study_channel_correlations.py (from the repository root; a few seconds).
"""

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def nu_elenbaas(el):
    """!
    @brief Elenbaas correlation in terms of the Elenbaas number of the spacing.
    @param el Elenbaas number of the spacing, El = 16 Ra*.
    @return Nusselt number based on the spacing S.
    """
    return el / 24.0 * (1.0 - np.exp(-35.0 / el)) ** 0.75


def nu_blend(el, m=-1.9):
    """!
    @brief Blend of the fully developed and the boundary-layer limits of Raithby and Hollands, in terms of the Elenbaas number of the spacing.
    @param el Elenbaas number of the spacing.
    @param m Blending exponent.
    @return Nusselt number based on the spacing S.
    """
    ra_b = el / 16.0
    nu_b = ((ra_b / 3.0) ** m + (0.62 * ra_b ** 0.25) ** m) ** (1.0 / m)
    return 2.0 * nu_b


def nu_bcr(el):
    """!
    @brief Composite correlation of Bar-Cohen and Rohsenow for isothermal plates as written in `research/theory/topics/13` (the paper was not opened): Nu_S = [576 / El^2 + 2.873 / El^(1/2)]^(-1/2).
    @param el Elenbaas number of the spacing.
    @return Nusselt number based on the spacing S.
    """
    return (576.0 / el ** 2 + 2.873 / np.sqrt(el)) ** -0.5


def main():
    """!
    @brief Print the comparison and the optimum spacing, and write out/channel_correlations.json for the figures.
    @return None.
    """
    el = np.logspace(-1, 4, 51)
    ratio = nu_blend(el) / nu_elenbaas(el) - 1.0
    print("| El (spacing) | Elenbaas Nu_S | blend Nu_S | Bar-Cohen and Rohsenow (as quoted) | blend / Elenbaas - 1 | quoted BCR / Elenbaas - 1 |")
    print("| --: | --: | --: | --: | --: | --: |")
    for e in (1.0, 10.0, 54.3, 100.0, 1000.0, 1e4):
        print(f"| {e:g} | {nu_elenbaas(e):.3f} | {nu_blend(e):.3f} | {nu_bcr(e):.3f} | {100 * (nu_blend(e) / nu_elenbaas(e) - 1):+.1f} % | {100 * (nu_bcr(e) / nu_elenbaas(e) - 1):+.1f} % |")
    grid = np.logspace(0, 3, 6001)
    out = {"el": el.tolist(), "elenbaas": nu_elenbaas(el).tolist(), "blend": nu_blend(el).tolist(), "bcr": nu_bcr(el).tolist()}
    print(f"\nMaximum difference between the two over El 0.1 to 1e4: {100 * np.abs(ratio).max():.1f} %")
    for name, f in (("Elenbaas", nu_elenbaas), ("blend", nu_blend), ("BCR", nu_bcr)):
        q = f(grid) / np.sqrt(grid)
        k = int(np.argmax(q))
        out["opt_" + name] = float(grid[k])
        print(f"Optimum El for the heat per unit of base area, {name}: {grid[k]:.1f} (S_opt proportional to El^(1/4): {grid[k] ** 0.25:.3f}); El_opt of the correlation quoted for Bar-Cohen and Rohsenow: 2.714^4 = {2.714 ** 4:.1f}; Simons: about 50")
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "channel_correlations.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
