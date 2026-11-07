#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_loss_split.py
@brief Where does the error at the corner come from? The heat lost through the edge by the 3D reference (copper and laminate) and by the FVM with the program's rule and with eta, and the temperature
       of the top copper along the edge.
@details Board 30 x 20 mm, 2 layers, 3.2 mm, h_s 200 W/m2K, 10 mm part of 2 W in the corner and at the centre; 3D solver with the side film split by slab (lib/layered3d_split.py, 0.5 mm, 8 sub-slabs)
         against the FVM at 0.5 mm (the FVM's face loss is h A theta on its top and bottom cells, the rest of the power is the edge). Run (repository root):
         .venv/bin/python research/laminate-edge-band/scripts/study_edge_loss_split.py
"""

import _bootband

import cases
import edge_rules as ER
import layered3d_split as L3
import numpy as np
from pcbthermal import SolverOptions, simulate


def split3d(c, dx=0.5, sub=8):
    """!
    @brief The 3D solution with the side loss split into copper and laminate.
    @param c Case tuple.
    @param dx Cell in mm.
    @param sub Sub-slabs per gap.
    @return Tuple (rise of the top slab maximum, side loss, copper share, laminate share, power, top field).
    """
    p, xy = cases.board(*c)
    b = p.board
    w, h, lay = int(round(b.width * 1000 / dx)), int(round(b.height * 1000 / dx)), b.layers
    g = b.gap_thicknesses()
    slabs = []
    for k in range(lay):
        slabs.append((35e-6, 385.0, 385.0, 1))
        if k < lay - 1:
            slabs.append((float(g[k]), 0.9, 0.3, sub))
    x0, y0 = xy
    top, out, side, dz = L3.solve_3d(dx * 1e-3, w, h, slabs, (x0 * 1e-3, y0 * 1e-3, (x0 + 10) * 1e-3, (y0 + 10) * 1e-3), p.total_power(), b.h_top, b.h_side or 0.0)
    return top.max(), side.sum(), side[0] + side[-1], side[1:-1].sum(), p.total_power(), top


def main():
    """!
    @brief Print the comparison.
    @return None
    """
    np.set_printoptions(linewidth=200, precision=1, suppress=True)
    for pos in ("corner", "centre"):
        c = (30, 20, 2, 3.2, 200.0, pos)
        t, s, cu, lam, P, top = split3d(c)
        print(f"{pos}: 3D rise {t:.2f}, side loss {s:.3f} W (copper {cu:.3f}, laminate {lam:.3f})")
        p, _ = cases.board(*c)
        for name, kw in (("program", {}), ("eta", dict(eta_mode="exact")), ("margin+hc", dict(band_width="margin", halfcell=True))):
            with ER.rule(**kw):
                r = simulate(p, SolverOptions(cell_mm=0.5, models=("fvm",))).results["fvm"]
            th = r.T - cases.T0
            face = p.board.h_top * (0.5e-3) ** 2 * (th[0].sum() + th[-1].sum())
            print(f"   FVM {name:10s} rise {r.t_max - cases.T0:6.2f}, side loss {P - face:.3f} W, top copper along the edge y = 0: {th[0][0, ::4][:12]}")
        if pos == "corner":
            print(f"   3D top slab along the edge y = 0                                            : {top[0, ::4][:12]}")


if __name__ == "__main__":
    main()
