#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_invariants.py
@brief Study 6: what must not change: the board without vias, the zone code switched off, the energy balance of the zoned network, the vias that conduct nothing, the symmetry of the board.
@details Checks, each printed as a number with its limit, on a few boards (the example board, a 4-layer plate with a 5 x 5 array under a 10 mm source, a 2-layer board, a board with an outline is NOT
         included: the Lumped model runs the equivalent rectangle there):
         1. a board WITHOUT vias: the zoned code and the program give the same temperature field (limit 1e-9 K, rounding of the sum order);
         2. the zone code switched off (`zones=False`) on a board with vias: the same as the program (limit 1e-9 K);
         3. a group of vias OUTSIDE every footprint: the same as the program (limit 1e-9 K);
         4. the energy balance of the zoned network: the heat leaving by the faces, the sides and the heatsinks equals the power (limit 1e-6 relative), and the residual of the linear system (limit 1e-9);
         5. vias that conduct nothing (plating 1e-12 m, open barrel; the true via effect is 0): the maximum with these vias against the maximum without any via, in K and in percent of the rise (the earlier
            folder found up to 2.8 K of E left, `lumped-via-groups` README 12.1; the limit here is the same, and the number for the 2.4.5 well with `Z_none` and `Z_cap` is the result);
         6. the symmetry: the array and the footprint mirrored in x (and rotated 90 degrees) give the same maximum (limit 0.05 K, the raster treats the two axes the same);
         7. the zone network of the same board at a 1 mm and 0.5 mm raster: the maximum temperature differs by less than the step of study 3 explains (printed, no limit).
Usage: python research/lumped-zones-adoption/scripts/study_invariants.py   (from the repository root; a few minutes)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import SolverOptions, simulate                               # noqa: E402


def field(problem, cell_mm=0.5):
    """!
    @brief The Lumped temperature field of a problem in the current patch state.
    @param problem The Problem.
    @param cell_mm Raster in mm.
    @return Tuple (T array, steady result).
    """
    res = simulate(problem, SolverOptions(models=("lumped",), cell_mm=cell_mm)).results["lumped"]
    return np.asarray(res.T), res


def boards():
    """!
    @brief The boards of the checks.
    @return dict label -> Problem.
    """
    import study_real_boards as srb
    zref.pc.load_libraries()
    return {"example board (9 vias)": srb.example(385.0, 0, 3.5),
            "4 layers, 5x5 @ 1.2 under 10 mm": zref.refs.make_problem(dict(n=5, pitch=1.2, src=10.0, fill=385.0)),
            "2 layers, 3x3 @ 2.0 under 8 mm": zref.refs.make_problem(dict(layers=2, n=3, pitch=2.0, src=8.0, fill=385.0))}


def main():
    """!
    @brief Run the checks and print the table.
    @return None.
    """
    print("| check | board | value | limit |\n| :-- | :-- | --: | --: |")
    for label, prob in boards().items():
        no_vias = copy.deepcopy(prob)
        no_vias.vias = []
        t_ref, _ = field(no_vias)
        with zl.patched():
            t_zon, _ = field(no_vias)
        print(f"| 1. no vias, zones on vs program (max |dT| K) | {label} | {np.abs(t_ref - t_zon).max():.2e} | 1e-9 |")
        t_ref, r_ref = field(prob)
        with zl.patched(zones=False):
            t_off, _ = field(prob)
        print(f"| 2. zones off vs program (max |dT| K) | {label} | {np.abs(t_ref - t_off).max():.2e} | 1e-9 |")
        with zl.patched(zone_macro="none"):
            t_z, r_z = field(prob)
        out = r_z.power_out
        bal = abs(sum(out.values()) - r_z.power_in) / r_z.power_in
        print(f"| 4. energy balance of the zoned field (|sum out - P| / P) | {label} | {bal:.2e} | 1e-6 |")
        print(f"| 4. residual of the linear system | {label} | {r_z.residual:.2e} | 1e-9 |")
    # 3. a group outside every footprint
    spec = dict(layers=4, n=3, pitch=3.5, dia=0.3, fill=385.0, side=30.0, src=6.0, offset=(10.0, 0.0), src_wh=(6.0, 6.0))
    prob = zref.refs.make_problem(spec)
    t_ref, _ = field(prob)
    with zl.patched():
        t_z, _ = field(prob)
    print(f"| 3. group outside the footprint, zones on vs program (max |dT| K) | 3x3 @ 3.5 mm, 10 mm from the centre | {np.abs(t_ref - t_z).max():.2e} | 1e-9 |")
    # 5. vias that conduct nothing
    print("\nvias that conduct nothing (plating 1e-12 m, open barrel): maximum with them minus the maximum without any via, K and percent of the rise\n")
    print("| board | rise without vias K | P245 | Z_none | Z_cap |\n| :-- | --: | --: | --: | --: |")
    for label, spec in (("5x5 @ 1.2 under 10 mm", dict(n=5, pitch=1.2, src=10.0, fill=0.0)), ("3x3 @ 3.0 under 12 mm", dict(n=3, pitch=3.0, src=12.0, fill=0.0)), ("7x7 @ 1.0 under 14 mm", dict(n=7, pitch=1.0, src=14.0, fill=0.0))):
        p = zref.refs.make_problem(spec)
        p.board.via_plating = 1e-12
        q0 = copy.deepcopy(p)
        q0.vias = []
        base = zref.pc.max_rise(q0, "lumped", 0.5)
        cells = []
        for name in ("P245", "Z_none", "Z_cap"):
            with zref.VARIANTS[name]():
                d = zref.pc.max_rise(p, "lumped", 0.5) - base
            cells.append(f"{d:+.2f} K ({100 * d / base:+.1f} %)")
        print(f"| {label} | {base:.2f} | " + " | ".join(cells) + " |")
    # 6. symmetry
    print("\nsymmetry: the same board with the array and the source moved by a mirror in x and by a rotation of 90 degrees, maximum rise in K\n")
    print("| variant | original | mirrored | rotated | spread |\n| :-- | --: | --: | --: | --: |")
    for name in ("P245", "Z_none", "Z_cap"):
        vals = []
        for kind in ("orig", "mirror", "rot"):
            p = zref.refs.make_problem(dict(n=5, pitch=1.2, src=10.0, fill=385.0, offset=(1.5, 0.0), src_wh=(12.0, 8.0)))
            c = p.board.width / 2
            for v in p.vias:
                if kind == "mirror":
                    v.x = 2 * c - v.x
                elif kind == "rot":
                    v.x, v.y = v.y, v.x
            if kind == "mirror":
                p.heaters[0].polygon = np.column_stack([2 * c - p.heaters[0].polygon[:, 0], p.heaters[0].polygon[:, 1]])
            elif kind == "rot":
                p.heaters[0].polygon = p.heaters[0].polygon[:, ::-1].copy()
            with zref.VARIANTS[name]():
                vals.append(zref.pc.max_rise(p, "lumped", 0.5))
        print(f"| {name} | " + " | ".join(f"{v:.3f}" for v in vals) + f" | {max(vals) - min(vals):.3f} |")
    # 7. raster
    print("\nthe same board at 1.0 and 0.5 mm, maximum rise in K\n")
    p = zref.refs.make_problem(dict(n=5, pitch=1.2, src=10.0, fill=385.0))
    for name in ("P245", "Z_none"):
        with zref.VARIANTS[name]():
            print(f"* {name}: " + ", ".join(f"{c:g} mm {zref.pc.max_rise(p, 'lumped', c):.3f}" for c in (1.0, 0.5)))


if __name__ == "__main__":
    with zref.released():           # "the program" of this study is the one-node network of 2.4.5 (the program has the zones since feature/lumped-zones)
        main()
