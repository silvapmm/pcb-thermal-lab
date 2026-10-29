#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_biot_definitions.py
@brief Why the effective conductivity of the coupon of Culham and Yovanovich falls at a high Biot number in the independent solver, and which definition of the mean wall temperature could give the plateau of the paper's Figure 5.
@details The paper plots the effective conductivity of its base laminate (FR4 / Cu / FR4 / Cu / FR4, 25 x 25 mm source on 50 x 50 mm) against the Biot number h L / k1 and shows a plateau of about 4.8 W/mK above Bi 100.
         Theories tested here, each by recomputing the effective conductivity of the same laminate: (A) mean wall temperature over the free top face and the bottom (the definition used elsewhere in this folder);
         (B) over the bottom only; (C) over the free top face only; (D) weighted by the heat flux; (E) the ambient (an ideal sink); and the variant with the film on the bottom face only. The mechanism is shown
         by comparing the solid-body resistance of the laminate with the series resistance of the stack under the footprint of the source, `sum t_i / (k_i A_source)`, which is what the heat meets when
         the films are so strong that it does not need to spread; and repeats h = 1000 W/m2K on three cell sizes (the fall is not a mesh effect).
         Run: .venv/bin/python research/effective-conductivity/scripts/study_biot_definitions.py (from the repository root; about 3 minutes).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
import layered3d as L                                          # noqa: E402
import study_culham_1998 as cu                                 # noqa: E402

MODES = ["A_top_free+bottom", "B_bottom_only", "C_top_free_only", "D_flux_weighted", "E_ambient"]


def r_solid(res, h_top, h_bottom, power, mode):
    """!
    @brief Solid-body resistance of a solution under one definition of the mean wall temperature.
    @param res Result of layered3d.solve().
    @param h_top Film coefficient on the free top face in W/m2K.
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param power Heat in W.
    @param mode One of MODES.
    @return float Resistance in K/W.
    """
    wt, wb = res["wall_top"], res["wall_bottom"]
    if mode == MODES[0]:
        w = np.concatenate([wt, wb]).mean()
    elif mode == MODES[1]:
        w = wb.mean()
    elif mode == MODES[2]:
        w = wt.mean() if wt.size else 0.0
    elif mode == MODES[3]:
        weights = np.concatenate([wt * h_top, wb * h_bottom])
        temps = np.concatenate([wt, wb])
        w = float((weights * temps).sum() / weights.sum())
    else:
        w = 0.0
    return (res["mean_source"] - w) / power


def keff(layers, h_top, h_bottom, mode, dx=1.25e-3, n=40, power=2.5):
    """!
    @brief Effective conductivity of a laminate under one definition (bisection on the single layer of the same thickness).
    @param layers List of (thickness, conductivity) from the top down.
    @param h_top Film coefficient on the free top face.
    @param h_bottom Film coefficient on the bottom face.
    @param mode One of MODES.
    @param dx Cell size in m.
    @param n Cells per side.
    @param power Heat in W.
    @return tuple (effective conductivity in W/mK, solid-body resistance of the laminate in K/W).
    """
    c = n * dx / 2
    src = (c - 12.5e-3, c - 12.5e-3, c + 12.5e-3, c + 12.5e-3)
    total = sum(t for t, _ in layers)
    res = L.solve(dx, n, n, cu.slabs(layers), src, power, h_top, h_bottom)
    target = r_solid(res, h_top, h_bottom, power, mode)
    a, b = np.log(0.2), np.log(80.0)
    for _ in range(26):
        m = 0.5 * (a + b)
        r = r_solid(L.solve(dx, n, n, [(total, float(np.exp(m)), 6)], src, power, h_top, h_bottom), h_top, h_bottom, power, mode)
        if r > target:
            a = m
        else:
            b = m
    return float(np.exp(0.5 * (a + b))), target


def plateau_check(h=1e4, k_plateau=4.8, dx=1.25e-3, n=40, power=2.5):
    """!
    @brief Can any laminate with this stack give the plateau of the paper? A lower bound of its solid-body resistance against the resistance the plateau implies.
    @details The source sits on the top FR4 layer, so all its heat crosses that layer: under the footprint alone its resistance is t1 / (k1 A_source), and the
             only way around it is sideways through the same FR4 to the free top face, a path of the order of the layer thickness along the perimeter of the source.
             The homogeneous layer of k = 4.8 W/mK under the same films has the resistance that the plateau would require of the laminate.
    @param h Film coefficient in W/m2K (a Biot number of 625).
    @param k_plateau Effective conductivity of the plateau in W/mK.
    @param dx Cell size in m.
    @param n Cells per side.
    @param power Heat in W.
    @return dict with the top-FR4 bound, the sideways escape estimate, the laminate resistance and the resistance of the plateau layer (K/W).
    """
    t1, k1 = cu.FR4
    a_src = 25e-3 ** 2
    c = n * dx / 2
    src = (c - 12.5e-3, c - 12.5e-3, c + 12.5e-3, c + 12.5e-3)
    total = sum(t for t, _ in cu.LAYERS[3])
    lam = L.solid_resistance(L.solve(dx, n, n, cu.slabs(cu.LAYERS[3]), src, power, h, h), power)
    plateau = L.solid_resistance(L.solve(dx, n, n, [(total, k_plateau, 6)], src, power, h, h), power)
    return {"top_fr4_bound": t1 / (k1 * a_src), "sideways_escape": 1.0 / (k1 * 4 * 25e-3), "laminate": lam, "plateau_layer": plateau, "h": h}


def mesh_check(h=1e3, cells=((2.5e-3, 20), (1.25e-3, 40), (0.625e-3, 80))):
    """!
    @brief The effective conductivity at a high film coefficient on three cell sizes (definition A), to show that the fall above Bi 60 is not a mesh effect.
    @param h Film coefficient in W/m2K.
    @param cells Tuples (cell size in m, cells per side) covering the 50 mm coupon.
    @return list of (cell size in mm, effective conductivity in W/mK).
    """
    return [(dx * 1e3, keff(cu.LAYERS[3], h, h, MODES[0], dx=dx, n=n)[0]) for dx, n in cells]


def main():
    """!
    @brief Print the tables and write out/biot_definitions.json for the figures.
    @return None.
    """
    base = cu.LAYERS[3]
    a_src = 25e-3 ** 2
    series = sum(t / (k * a_src) for t, k in base)
    pc = plateau_check()
    print(f"Plateau check at h = {pc['h']:g} W/m2K (Bi {pc['h'] * 0.025 / 0.4:g}): the top FR4 under the source alone is {pc['top_fr4_bound']:.2f} K/W, the sideways escape to the free "
          f"top face about {pc['sideways_escape']:.0f} K/W, the laminate {pc['laminate']:.2f} K/W; a homogeneous layer of 4.8 W/mK gives {pc['plateau_layer']:.2f} K/W, "
          f"{pc['top_fr4_bound'] / pc['plateau_layer']:.1f} times below the bound")
    hs = (0.1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5)
    out = {"series_under_source": series, "h": list(hs), "modes": {}, "bottom_only_film": [], "R_solid": [], "plateau_check": pc}
    mc = mesh_check()
    out["mesh_check"] = mc
    print(f"Mesh check at h = 1000 W/m2K (definition A): " + ", ".join(f"{k:.2f} W/mK with {d:g} mm cells" for d, k in mc))
    print(f"Series resistance of the stack under the footprint of the source: {series:.2f} K/W")
    print("| h (W/m2K) | Bi = h L / k1 | " + " | ".join(MODES) + " | film on the bottom only | R_solid (A) (K/W) |")
    print("| --: | --: | " + " | ".join("--:" for _ in MODES) + " | --: | --: |")
    for h in hs:
        row = {m: keff(base, h, h, m)[0] for m in MODES}
        rb = keff(base, 0.0, h, MODES[1])[0]
        rs = keff(base, h, h, MODES[0])[1]
        for m in MODES:
            out["modes"].setdefault(m, []).append(row[m])
        out["bottom_only_film"].append(rb)
        out["R_solid"].append(rs)
        print(f"| {h:g} | {h * 0.025 / 0.4:.3g} | " + " | ".join(f"{row[m]:.2f}" for m in MODES) + f" | {rb:.2f} | {rs:.2f} |", flush=True)
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "biot_definitions.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
