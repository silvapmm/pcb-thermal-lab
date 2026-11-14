#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_definitions.py
@brief Study 1: what "the temperature of the part" means in each model, on a part over a dense via group, before any model is compared.
@details For one synthetic board (a 6 or 8 mm part over a 5 x 5 array, 1 mm pitch, 0.3 mm drill, two or four layers) it prints, per model, every number that can be called "the part
         temperature": for the Lumped (zoned) the nodes A and C, the three candidates of the peak, `heater_peak`, the painted field (core painted with C) maximum and mean under the
         footprint and the value `heater_stats` returns; for the one-node Lumped the same; for the FVM the node values under the footprint (maximum, mean, and the maximum
         against the cell: 1, 0.5, 0.25 mm); for the independent 3D solver (barrels drawn) the cell maximum and mean of the surface under the part at 0.25 and 0.125 mm. The
         point is to say which pairs are the same quantity.
Usage: python research/lumped-dense-via-group/scripts/study_definitions.py   (from the repository root, with the program's .venv; ONE process)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
import ref3d                                                                  # noqa: E402
from pcbthermal import lumped, viaconstriction                                # noqa: E402
from pcbthermal.lumped import Network                                         # noqa: E402


def lumped_nodes(p, zoned):
    """!
    @brief Internals of the Lumped network of the first heater: nodes and the candidates of the peak.
    @param p Problem.
    @param zoned True for the zoned network, False for the one-node.
    @return dict of numbers (degC where absolute, K where relative to the ambient).
    """
    old = lumped.ZONES
    lumped.ZONES = zoned
    try:
        cell = lumped.cell_for(p, 1.0)
        b = p.board
        nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
        net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
        vias = viaconstriction.ViaSet(p)
        h = p.heaters[0]
        ok = lumped.will_be_zoned(p, h, vias=vias) if zoned else False
        rn = lumped._heater_network(net, lumped._footprint_coverage(net, h), h.layer, h.power, 10, vias, ok)
        th = rn["theta"]
        amb = b.ambient
        out = {"cell_mm": cell, "zoned": "core" in rn, "A_or_node": amb + th[0, 0], "peak_extra_K": rn["peak_extra"]}
        if "core" in rn:
            pk = rn["peak"]
            l = h.layer
            q_in = (th[l, 0] - th[l, 1]) / pk.r_ac
            q_out = (th[l, 0] - th[l, 2]) / pk.r_a2 if pk.r_a2 is not None and np.isfinite(pk.r_a2) else 0.0
            cand_a = float(np.max(pk.fields @ np.array([q_in, q_out]))) if q_in + q_out > 0 else 0.0
            bump = (th[l, 1] - th[l, 0]) / pk.r_ac * pk.bump if th[l, 1] > th[l, 0] else 0.0
            out.update({"C": amb + th[0, 1], "micro_K": pk.micro_rise(th), "bump_K": bump, "cand_field_of_A_K": cand_a,
                        "cand_C_micro_bump_K": th[l, 1] + pk.micro_rise(th) + bump - th[l, 0], "core_cells": int(rn["core"].sum())})
        out["peak_degC"] = amb + th[0, 0] + rn["peak_extra"]
        return out
    finally:
        lumped.ZONES = old


def main():
    """!
    @brief Print the definitions table for the base board at two and four layers.
    @return None.
    """
    for layers, part in ((2, 8.0), (4, 8.0), (2, 6.0)):
        print(f"\n## {layers} layers, {part:g} mm part, 5 x 5 vias at 1 mm pitch, 0.3 mm drill, 3 W, 100 x 80 mm, h 10 W/m2K\n")
        p = v.board(layers, 5, 1.0, 0.3, part)
        z = lumped_nodes(p, True)
        o = lumped_nodes(p, False)
        print("Lumped zoned:", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in z.items()})
        print("Lumped one node:", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in o.items()})
        for m in ("lumped", "lumped1"):
            r = v.run(p, m, 1.0)
            res = r["res"]
            T = res.T[0]
            from pcbthermal.geometry import coverage_fraction
            cov = coverage_fraction(p.heaters[0].polygon, T.shape[1], T.shape[0], res.dx, res.dy, 4)
            print(f"{m}: heater_stats peak {r['parts'][0]['peak']:.3f}  mean {r['parts'][0]['mean']:.3f}  heater_peak {r['heater_peak'][0]:.3f}  "
                  f"painted field max under footprint {T[cov > 0].max():.3f}  painted mean {np.average(T, weights=cov):.3f}  board max {r['board']:.3f}")
        for c in (1.0, 0.5, 0.25):
            r = v.run(p, "fvm", c)
            print(f"fvm {c} mm: peak (cell max under footprint) {r['parts'][0]['peak']:.3f}  mean {r['parts'][0]['mean']:.3f}  board max {r['board']:.3f}")
        r = v.run(p, "solid3d", 1.0)
        print(f"solid3d 1.0 mm: peak {r['parts'][0]['peak']:.3f}  mean {r['parts'][0]['mean']:.3f}  board {r['board']:.3f}")
    # The independent reference on the 40 x 40 mm version of the board (quadrant, barrels drawn)
    print("\n## independent 3D (layered3d, barrels drawn), 40 x 40 mm, 2 layers, 8 mm part, 5 x 5 at 1 mm\n")
    p = v.board(2, 5, 1.0, 0.3, 8.0, size=(40.0, 40.0))
    p.board.h_side = 0.0
    for dx in (0.25, 0.125):
        print("3D", dx, "mm", {k: round(x, 3) if isinstance(x, float) else x for k, x in ref3d.solve(p, dx).items()})
    for m, c in (("fvm", 0.5), ("fvm", 0.25), ("lumped", 1.0), ("lumped1", 1.0), ("solid3d", 0.5)):
        r = v.run(p, m, c)
        print(m, c, {k: round(x, 3) for k, x in r["parts"][0].items()}, "board", round(r["board"], 3))


if __name__ == "__main__":
    main()
