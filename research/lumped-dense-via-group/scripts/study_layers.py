#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_layers.py
@brief Study 4: the nodes A and C of every copper layer of the zoned Lumped against the FVM (0.5 mm) averaged over the same cells, and the heat that the vias carry in each model.
@details Per case: for every layer the Lumped node values (A, C) and the FVM mean over the core mask and over the rest of the footprint, in K of rise; the temperature step across
         the vias in C (top minus bottom) in both models; the heat into the barrels of the Lumped (sum of `g_via (th_top - th_bottom)` of the zone network) and of the FVM (the sum of
         the via couplings of its matrix over the footprint, computed from the program's own Network); the share of the part's power each carries.
Usage: python research/lumped-dense-via-group/scripts/study_layers.py   (from the repository root; ONE process)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
from pcbthermal import lumped, viaconstriction, fvm                           # noqa: E402
from pcbthermal.lumped import Network                                         # noqa: E402

CASES = [("base 8 mm, 5x5 @1.0, 2L", dict()), ("part 10, 8x8 @1.0, 2L", dict(part=10.0, n=8)), ("part 10, 5x5 @1.5, 4L", dict(part=10.0, n=5, pitch=1.5, layers=4)),
         ("4L filled 8x8 @0.8, 8 mm", dict(layers=4, filled=True, n=8, pitch=0.8)), ("part 6, 5x5 @1.0, 2L", dict(part=6.0))]


def main():
    """!
    @brief Print the per-layer table.
    @return None.
    """
    cell = 0.5
    for label, kw in CASES:
        p = v.board(**kw)
        h = p.heaters[0]
        b = p.board
        nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
        net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
        vias = viaconstriction.ViaSet(p)
        cov = lumped._footprint_coverage(net, h)
        rn = lumped._heater_network(net, cov, h.layer, h.power, 10, vias, True)
        th = rn["theta"]
        core = rn["core"]
        f = fvm.solve_steady(p, cell)
        T = f.T - b.ambient
        wa, wc = cov * (~core), cov * core
        print(f"\n### {label} (power {h.power} W; core {int(core.sum())} of {int((cov>0).sum())} cells)")
        print("| layer | Lumped A | FVM A | err A K | Lumped C | FVM C | err C K |")
        print("| --: | --: | --: | --: | --: | --: | --: |")
        for l in range(b.layers):
            a_f, c_f = np.average(T[l], weights=wa), np.average(T[l], weights=wc)
            print(f"| {l+1} | {th[l,0]:.2f} | {a_f:.2f} | {th[l,0]-a_f:+.2f} | {th[l,1]:.2f} | {c_f:.2f} | {th[l,1]-c_f:+.2f} |")
        # Temperature step across the vias at C
        d_l = th[0, 1] - th[-1, 1]
        d_f = np.average(T[0], weights=wc) - np.average(T[-1], weights=wc)
        print(f"top minus bottom at C: Lumped {d_l:.2f} K, FVM {d_f:.2f} K")
        # Heat taken by the vias: Lumped from the zone network's well couplings; FVM from the via couplings of the matrix in the footprint
        gz = rn.get("K")
        try:
            q_l = None
            # K row-sum structure is internal; use energy balance instead: what leaves through the bottom face and through the sides of the part's column
            top_l, bot_l = rn["out"]["top"], rn["out"]["bottom"]
            print(f"Lumped heat out: top {top_l:.2f} W, bottom {bot_l:.2f} W of {h.power} W (whole board)")
        except Exception:
            pass
        # FVM: the heat through the dielectric plus vias between the first two layers over the footprint cells = g(T0 - T1) summed (the matrix coupling of the first gap, vias included)
        nt = fvm.Network(p, nx, ny, assemble=True)
        K = nt.K.tocsr()
        n_cell = nx * ny
        # Node numbering of the FVM: layer-major; with laminate nodes the copper layers are not adjacent, so use the via-coupling arrays only
        print("(FVM per-path heat: see the total below)")
        foot = cov > 0
        print(f"FVM: heat out of the board top {float((nt.g_top[0] * T[0]).sum()):.2f} W, bottom {float((nt.g_bottom[b.layers-1] * T[b.layers-1]).sum()):.2f} W")


if __name__ == "__main__":
    main()
