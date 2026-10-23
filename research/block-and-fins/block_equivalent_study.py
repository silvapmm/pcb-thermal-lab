"""!
@file block_equivalent_study.py
@brief Can the Lumped and Analytic models represent a metal block? Two approaches against the FVM, which has the block.

@details A. **Equivalent coefficient with contact area and an annular fin** (works in both models): the block is replaced by a plain heatsink. The heat enters the block only over
            the copper under it (contact area A_c), crosses the interface R'' and leaves from the whole exposed face of the block (area A_p, coefficient h_exp = face h x fin ratio
            + extra h); the part of the block outside the contact is an annular fin of conductance k t (single-sided, m = sqrt(h_exp / (k t)), inner radius r1 = sqrt(A_c / pi),
            outer radius r2 = sqrt(A_p / pi), adiabatic edge). Per unit of contact area h_eq = 1 / (R'' + 1 / (h_exp (1 + eta A_out / A_c))), spread as an extra coefficient of
            (h_eq - h_face) A_c / A_p over the polygon. 'old' is the earlier equivalent (isothermal block over the whole polygon, no fin) for comparison.
         B. **The block as one more layer of the ring network** (Lumped only): the block layer of the FVM network is aggregated into rings like the board layers (`lumped.solve_steady(block_nodes=True)`).
         C. **The block as a graph of tiles inside the Green-function correction** (Analytic only): the block temperatures are eliminated into a Schur complement that couples the
            tiles of the board layer under the block (`analytic.solve_steady(block_tiles=True)`).

         The error is the difference of the maximum temperature divided by the FVM rise above ambient, in percent.

Usage: python research/block-and-fins/block_equivalent_study.py
"""

import copy
import itertools
import math
import os
import sys

import numpy as np
from scipy.special import i0, i1, k0, k1

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import Problem, SolverOptions, analytic, blocks, fvm, lumped, simulate     # noqa: E402,F401
from pcbthermal.geometry import coverage_fraction, polygon_area                              # noqa: E402


def annular_fin_efficiency(m, r1, r2):
    """!
    @brief Efficiency of an annular fin with an adiabatic tip.
    @param m sqrt(h / (k t)) of the fin in 1/m (single-sided).
    @param r1 Inner radius in m.
    @param r2 Outer radius in m.
    @return Efficiency (heat divided by that of an isothermal fin), 1 when the fin has no length.
    """
    if r2 <= r1:
        return 1.0
    num = k1(m * r1) * i1(m * r2) - i1(m * r1) * k1(m * r2)
    den = i0(m * r1) * k1(m * r2) + k0(m * r1) * i1(m * r2)
    return float(2.0 * r1 / (m * (r2 ** 2 - r1 ** 2)) * num / den)


def equivalent(problem, spreading=True):
    """!
    @brief The problem with every metal block replaced by a plain heatsink (approach A, or 'old' with spreading=False).
    @param problem A Problem.
    @param spreading True for the contact area and the annular fin, False for the earlier isothermal block over the whole polygon.
    @return Copy of the problem without blocks.
    """
    p = copy.deepcopy(problem)
    b = p.board
    for s in p.heatsinks:
        if not s.is_block():
            continue
        h_face = b.h_top if (s.layer == 0 or b.layers == 1) else b.h_bottom
        h_exp = blocks.exposed_h(s, h_face)
        r_c = max(s.interface_resistance(), 1e-7)
        a_p = polygon_area(s.polygon)
        if spreading:
            nx, ny = int(round(b.width * 1000)), int(round(b.height * 1000))
            dx, dy = b.width / nx, b.height / ny
            cov = coverage_fraction(s.polygon, nx, ny, dx, dy, samples=4)
            fill = np.zeros((ny, nx))
            for z in p.zones:
                if z.layer == s.layer:                                    # Copper of the block's layer under the block
                    fill = np.maximum(fill, coverage_fraction(z.polygon, nx, ny, dx, dy, samples=4) * z.fill)
            a_c = float((cov * fill).sum() * dx * dy)
            if a_c <= 0.0:
                s.h_extra, s.thickness = 0.0, 0.0
                s.fin_height = s.fin_thickness = s.fin_pitch = 0.0
                continue
            eta = annular_fin_efficiency(math.sqrt(h_exp / (s.k * s.thickness)), math.sqrt(a_c / math.pi), math.sqrt(a_p / math.pi))
            h_eq = 1.0 / (r_c + 1.0 / (h_exp * (1.0 + eta * (a_p - a_c) / a_c)))
            extra = (h_eq - h_face) * a_c / a_p
        else:
            extra = 1.0 / (r_c + 1.0 / h_exp) - h_face
        s.h_extra, s.thickness = max(extra, 0.0), 0.0
        s.fin_height = s.fin_thickness = s.fin_pitch = 0.0
    return p


def make_case(rect, pad, thickness, k, r_c, fins=None):
    """!
    @brief The 100 x 80 mm, two-layer board of the tests: 5 W on the top, a copper pad on the bottom and a block under it.
    @param rect Block rectangle (x0, y0, x1, y1) in mm.
    @param pad Bottom copper rectangle in mm.
    @param thickness Block thickness in mm.
    @param k Conductivity of the block in W/mK.
    @param r_c Interface resistance in m2K/W.
    @param fins None or (height, thickness, pitch) in mm.
    @return Problem.
    """
    p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=pad)
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    kw = {} if fins is None else dict(fin_height_mm=fins[0], fin_thickness_mm=fins[1], fin_pitch_mm=fins[2])
    p.add_heatsink(2, 0.0, rect=rect, thickness_mm=thickness, k=k, contact_r=r_c, **kw)
    return p


def cases():
    """!
    @brief The family of test cases: block size and pad, thickness, metal, interface and fins.
    @return List of (label, Problem).
    """
    out = []
    geoms = {"pad 30x30 in block 60x60": ((20, 10, 80, 70), (35, 25, 65, 55)), "pad 50x40 in block 90x70": ((5, 5, 95, 75), (25, 20, 75, 60)),
             "pad = block 40x40": ((30, 20, 70, 60), (30, 20, 70, 60)), "pad 20x20 in block 80x60": ((10, 10, 90, 70), (40, 30, 60, 50))}
    for (gname, (rect, pad)), thick, (mname, k), r_c in itertools.product(geoms.items(), (1.0, 3.0, 6.0), (("Al", 204.0), ("Cu", 386.0), ("steel", 50.0)), (1e-4, 5e-4, 2e-3)):
        if (thick, mname) not in ((1.0, "Al"), (3.0, "Al"), (6.0, "Al"), (3.0, "Cu"), (3.0, "steel"), (1.0, "steel")):
            continue
        out.append((f"{gname}, {thick:g} mm {mname}, R''={r_c * 1e4:g} Kcm²/W", make_case(rect, pad, thick, k, r_c)))
    out.append(("pad 30x30 in block 60x60, 3 mm Al + fins 15/1.5/8", make_case((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4, fins=(15.0, 1.5, 8.0))))
    out.append(("pad 50x40 in block 90x70, 3 mm Al + fins 15/1.5/8", make_case((5, 5, 95, 75), (25, 20, 75, 60), 3.0, 204.0, 5e-4, fins=(15.0, 1.5, 8.0))))
    return out


def main(limit=None):
    """!
    @brief Print the error table of the approaches for every case and the summary.
    @param limit Optional maximum number of cases (quick runs).
    """
    rows = []
    print("| Case | FVM rise (K) | old (L / A) | A fin (L / A) | B node (L) | C tiles (A) |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for label, p in cases()[:limit]:
        ref = fvm.solve_steady(p, 1.0)
        rise = ref.t_max - 25.0
        old, new = equivalent(p, False), equivalent(p, True)
        e = {}
        for name, q in (("old", old), ("A", new)):
            e[name] = tuple((m.solve_steady(q, cell_mm=1.0).t_max - ref.t_max) / rise * 100.0 for m in (lumped, analytic))
        e["B"] = (lumped.solve_steady(p, cell_mm=1.0, block_nodes=True).t_max - ref.t_max) / rise * 100.0
        e["C"] = (analytic.solve_steady(p, cell_mm=1.0, block_tiles=True).t_max - ref.t_max) / rise * 100.0
        rows.append((e["old"], e["A"], e["B"], e["C"]))
        print(f"| {label} | {rise:.1f} | {e['old'][0]:+.1f} / {e['old'][1]:+.1f} | {e['A'][0]:+.1f} / {e['A'][1]:+.1f} | {e['B']:+.1f} | {e['C']:+.1f} |", flush=True)
    a = np.array([[r[0][0], r[0][1], r[1][0], r[1][1], r[2], r[3]] for r in rows])
    print("\nmean absolute error (%), max absolute error (%):")
    for j, name in enumerate(("old Lumped", "old Analytic", "A Lumped", "A Analytic", "B Lumped", "C Analytic")):
        print(f"  {name:13s} {np.abs(a[:, j]).mean():5.1f}  {np.abs(a[:, j]).max():5.1f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
