#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_culham_1998.py
@brief Repeat the test coupons of Culham and Yovanovich (ITherm 1998) with an independent 3D finite-volume solver and compare the effective conductivity with the values the paper reports.
@details The coupon is a 50 x 50 mm block of five layers (FR4 0.5263 mm, copper 0.0356 mm), a concentric 25 x 25 mm source of 2.5 W on the top face (the rest of the top face and the bottom face convect
         with h = 5 W/m2K, the sides are insulated). The paper replaces the laminate by a single layer of the same thickness and boundary conditions whose solid-body resistance
         (mean source temperature minus mean wall temperature, over the power) is the same, and calls its conductivity the effective conductivity. Studies: A the order of the layers (the five cases of
         the paper's Table 2), B the relative size of the source (epsilon = source area / board area), C the source position, D the film coefficient (Biot number), and the series and parallel limits; and the base case with the stack thinned to the 1.62 mm the text states.
         The reference values are those printed in the text (15.02, 5.00, 8.28, +42 %, +67 %, 17.62, 0.42, 9.02, 2.71, 0.82) or read from the plotted points of the figures (marked "plot", about +-0.5 W/mK).
         Run: .venv/bin/python research/effective-conductivity/scripts/study_culham_1998.py [--mesh-check] (from the repository root; about 15 minutes, 2 more with --mesh-check).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import layered3d as L                                          # noqa: E402

DX = 0.5e-3                                                   # cell size (m): the 25 mm source edges fall on cell edges
N = 100                                                       # cells per side: 50 mm
FR4 = (0.5263e-3, 0.4)
CU = (0.0356e-3, 400.0)
POWER = 2.5
H = 5.0

LAYERS = {                                                    # Table 2 of the paper, from the top down (thickness m, k W/mK)
    1: [CU, CU, FR4, FR4, FR4],
    2: [CU, FR4, FR4, FR4, CU],
    3: [FR4, CU, FR4, CU, FR4],
    4: [(0.7895e-3, 0.4), CU, CU, (0.7895e-3, 0.4)],
    5: [FR4, FR4, FR4, CU, CU],
}
PAPER_LAYERS = {1: (15.02, "text"), 2: (11.6, "plot"), 3: (8.28, "text"), 4: (7.4, "plot"), 5: (5.00, "text")}
SIZES = {0.01: (3.4, "plot"), 0.1: (7.6, "plot"), 0.25: (8.28, "text"), 0.5: (6.8, "plot"), 1.0: (0.42, "text")}
BIOT = {0.1: (8.6, "plot"), 1.0: (8.3, "plot"), 10.0: (8.3, "plot"), 100.0: (6.0, "plot"), 1e3: (4.8, "plot"), 1e4: (4.8, "plot")}   # keyed by h; read from the paper's Figure 5


def slabs(layers, n_cu=1, n_fr4=3):
    """!
    @brief Convert a layer list into the (thickness, k, sub-slabs) list of the solver.
    @param layers List of (thickness, conductivity) from the top down.
    @param n_cu Sub-slabs per copper layer.
    @param n_fr4 Sub-slabs per dielectric layer.
    @return list of (thickness, k, n).
    """
    return [(t, k, n_cu if k > 100 else n_fr4) for t, k in layers]


def effective(layers, source, h_top=H, h_bottom=H, power=POWER):
    """!
    @brief Solid-body resistance of a laminate and the effective conductivity of the single layer with the same resistance.
    @param layers List of (thickness, conductivity) from the top down.
    @param source Source rectangle (x0, y0, x1, y1) in m.
    @param h_top Film coefficient on the free top face in W/m2K.
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param power Heat in W.
    @return tuple (effective conductivity in W/mK, solid-body resistance in K/W).
    """
    res = L.solve(DX, N, N, slabs(layers), source, power, h_top, h_bottom)
    r = L.solid_resistance(res, power)
    total = sum(t for t, _ in layers)
    return L.effective_conductivity(DX, N, N, total, source, power, h_top, h_bottom, r, n_sub=6, lo=0.3, hi=60.0), r


def centred(side):
    """!
    @brief A square source of the given side at the centre of the 50 mm board.
    @param side Side in m.
    @return tuple (x0, y0, x1, y1).
    """
    c = N * DX / 2
    return (c - side / 2, c - side / 2, c + side / 2, c + side / 2)


def thickness_check(total=1.62e-3):
    """!
    @brief The base case (FR4-Cu-FR4-Cu-FR4) with the three FR4 layers thinned so that the stack has the 1.62 mm of the paper's text instead of the 1.6501 mm its layers add to.
    @param total Total thickness in m.
    @return tuple (FR4 layer thickness in m, effective conductivity in W/mK).
    """
    fr4 = (total - 2 * CU[0]) / 3
    layers = [(fr4, FR4[1]) if k < 100 else (t, k) for t, k in LAYERS[3]]
    return fr4, effective(layers, centred(25e-3))[0]


def mesh_check(cells=(2.5e-3, 1.25e-3, 0.625e-3, 0.5e-3)):
    """!
    @brief The effective conductivity of the base case on several cell sizes, to show that the steady shortfall against the paper is not a mesh effect.
    @param cells Cell sizes in m (the 25 mm source edges must fall on cell edges).
    @return list of (cell size in mm, effective conductivity in W/mK).
    """
    global DX, N
    saved = DX, N
    out = []
    try:
        for dx in cells:
            DX, N = dx, int(round(50e-3 / dx))
            out.append((dx * 1e3, effective(LAYERS[3], centred(25e-3))[0]))
    finally:
        DX, N = saved
    return out


def main():
    """!
    @brief Run the studies, print the tables and write out/culham_1998.json for the figures.
    @return None.
    """
    out = {"limits": {}, "layers": {}, "sizes": {}, "location": {}, "biot": {}}
    base = LAYERS[3]
    total = sum(t for t, _ in base)
    kp = sum(t * k for t, k in base) / total
    ks = total / sum(t / k for t, k in base)
    out["limits"] = {"in_plane": kp, "cross_plane": ks, "arithmetic": (kp + ks) / 2, "geometric": float(np.sqrt(kp * ks)), "harmonic": 2 * kp * ks / (kp + ks), "total_thickness_mm": total * 1e3}
    print(f"Limits (paper: 17.62, 0.42, 9.02, 2.71, 0.82): in-plane {kp:.2f}, cross-plane {ks:.3f}, arithmetic {(kp + ks) / 2:.2f}, geometric {np.sqrt(kp * ks):.2f}, harmonic {2 * kp * ks / (kp + ks):.2f}; the layers add to {total * 1e3:.4f} mm (the paper says 1.62)")
    print("\n| Case (layers from the top) | this work (W/mK) | paper (W/mK) | source of the paper value | difference |")
    print("| :-- | --: | --: | :-- | --: |")
    for c, lay in LAYERS.items():
        ke, r = effective(lay, centred(25e-3))
        ref, how = PAPER_LAYERS[c]
        out["layers"][c] = {"k_eff": ke, "R": r, "paper": ref, "how": how}
        names = "-".join("Cu" if k > 100 else "FR4" for _, k in lay)
        print(f"| {c}: {names} | {ke:.2f} | {ref} | {how} | {100 * (ke / ref - 1):+.1f} % |", flush=True)
    print("\n| epsilon (source area / board area) | side (mm) | this work (W/mK) | paper (W/mK) | source | difference |")
    print("| --: | --: | --: | --: | :-- | --: |")
    for eps, (ref, how) in SIZES.items():
        side = 1e-3 * round(np.sqrt(eps) * 50.0)               # whole millimetres, so that the edges of a centred source fall on the 0.5 mm cells
        if eps == 1.0:
            src = (0, 0, N * DX, N * DX)
        else:
            src = centred(side)
        ke, r = effective(base, src)
        out["sizes"][eps] = {"side_mm": side * 1e3, "k_eff": ke, "paper": ref, "how": how}
        print(f"| {eps} | {side * 1e3:.1f} | {ke:.2f} | {ref} | {how} | {100 * (ke / ref - 1):+.1f} % |", flush=True)
    print("\n| source position (assumed layouts) | this work (W/mK) | paper | difference |")
    print("| :-- | --: | --: | --: |")
    s = 25e-3
    base_ke = out["sizes"][0.25]["k_eff"]
    for name, src, ref in (("flush with one edge, centred on it (case 2?)", (0, 12.5e-3, s, 12.5e-3 + s), 8.28 * 1.42), ("in a corner (case 3?)", (0, 0, s, s), 8.28 * 1.67)):
        ke, r = effective(base, src)
        out["location"][name] = {"k_eff": ke, "paper": ref}
        print(f"| {name} | {ke:.2f} | {ref:.2f} (+42 % / +67 % of 8.28) | {100 * (ke / ref - 1):+.1f} % |", flush=True)
    print("\n| film coefficient h (W/m2K) | Biot = h L / k1, L = 25 mm, k1 = 0.4 | this work (W/mK) | paper (plot) | difference |")
    print("| --: | --: | --: | --: | --: |")
    for h in (0.1, 1.0, 10.0, 100.0, 1e3, 1e4):
        ke, r = effective(base, centred(25e-3), h, h)
        bi = h * 0.025 / 0.4
        ref, how = BIOT[h]
        out["biot"][h] = {"Bi": bi, "k_eff": ke, "paper": ref, "how": how}
        print(f"| {h:g} | {bi:.3g} | {ke:.2f} | {ref} | {100 * (ke / ref - 1):+.1f} % |", flush=True)
    fr4, ke = thickness_check()
    out["thickness_check"] = {"fr4_mm": fr4 * 1e3, "k_eff": ke}
    print(f"\nBase case with the stack thinned to the 1.62 mm of the text (FR4 layers of {fr4 * 1e3:.4f} mm): {ke:.2f} W/mK, "
          f"{100 * (ke / 8.28 - 1):+.1f} % from the paper's 8.28 (1.6501 mm: {out['sizes'][0.25]['k_eff']:.2f})")
    if "--mesh-check" in sys.argv:
        mc = mesh_check()
        out["mesh_check"] = mc
        print("Base case on several cell sizes: " + ", ".join(f"{k:.2f} W/mK with {d:g} mm cells" for d, k in mc))
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "culham_1998.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
