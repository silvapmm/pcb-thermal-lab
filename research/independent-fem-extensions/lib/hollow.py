#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file hollow.py
@brief The strong-edge board of `independent-fem-edge` (3(b)) with HOLLOW plated vias: conforming O-grid cylinders with rings across the plated wall, a core that is
       open (a hole through the board), filled with resin or filled with copper; single vias and a 3 x 3 array. Study 1 of the finite-element extensions.
@details Uses `independent-fem-edge/lib` as it is (imported, never edited). The wall of a hollow barrel is `r_in <= r < r_drill` (copper); the core `r < r_in` is a
         separate set of elements: removed from the plan for an open barrel (adiabatic inner wall, as the program's open barrel; the hole carries no film on its wall
         and none on the top and bottom faces), `k_fill` for a resin or copper fill. SI units; lengths of the builders in mm like `cases.py`.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "independent-fem-edge", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import board                                                            # noqa: E402
import cases                                                            # noqa: E402
import mesh2d                                                           # noqa: E402

MM = 1e-3
PLATING = 25e-6                                                         # barrel plating, the program's `board.via_plating`


def wall_radii(r_drill_mm, plating_mm=0.025, n_wall=3):
    """!
    @brief Circle levels across the plated wall of a hollow barrel.
    @param r_drill_mm Drill radius in mm.
    @param plating_mm Plating thickness in mm (0: a solid cylinder, one level).
    @param n_wall Elements across the wall.
    @return list of radii in mm, increasing, the last one the drill radius.
    """
    if plating_mm <= 0:
        return [r_drill_mm]
    r_in = r_drill_mm - plating_mm
    return list(np.linspace(r_in, r_drill_mm, n_wall + 1))


def strong_board(h_side, vias, hf=0.2, n_gap=6, growth=1.3, hmax=0.5, via_r=0.15, plating=0.025, core="open", n_wall=3, n_side_via=8, power=0.5, half_win=None):
    """!
    @brief The 10 x 10 mm, four-layer strong-edge board (half domain y <= 5 mm) with any number of hollow or solid vias on the symmetry line or off it.
    @param h_side Wall film W/m2K.
    @param vias List of (cx_mm, cy_mm) via centres (y <= 5 mm; a centre on y = 5 is cut by the symmetry plane).
    @param hf Fine plan size in mm.
    @param n_gap Elements per gap.
    @param growth Growth of the plan size away from a fine zone.
    @param hmax Largest plan size in mm.
    @param via_r Drill radius in mm.
    @param plating Barrel wall in mm (0: solid cylinder of copper).
    @param core 'open' (hole), 'solid' (copper, the cylinder of 3(b) when plating is 0), or a conductivity in W/mK for a fill.
    @param n_wall Elements across the wall.
    @param n_side_via Intervals per side of the via window (and of its inner square).
    @param power Source power of the whole board in W (the half domain carries half).
    @param half_win Half side of the via window in mm (default min(distance to the wall, 0.5), 0.4 when several vias).
    @return Board.
    """
    W = 10.0
    bx, zx = [0, 1, 4, W], [(0, 0.6), (W - 0.6, W), (0.4, 1.6), (3.4, 4.6)]
    by, zy = [0, 4, 5], [(0, 0.6), (3.4, 5)]
    wins = []
    for cx, cy in vias:
        half = half_win if half_win is not None else (min(W - cx, 0.4 if len(vias) > 1 else 0.5))
        wins.append((cx, cy, half))
        zx.append((cx - half - 0.3, min(cx + half + 0.3, W)))
        zy.append((cy - half - 0.3, min(cy + half, 5.0)))
    xn = cases.axis(W, bx, zx, hf, growth, hmax)
    yn = cases.axis(5.0 + max([w[2] for w in wins] + [0]), by + [5.0], zy, hf, growth, hmax)
    for cx, cy, half in wins:
        xn = mesh2d.uniform_window(xn, (cx - half) * MM, (cx + half) * MM, n_side_via)
        yn = mesh2d.uniform_window(yn, (cy - half) * MM, (cy + half) * MM, n_side_via)
    plan = mesh2d.tensor(xn, yn)
    radii_all = wall_radii(via_r, plating, n_wall)
    for cx, cy, half in wins:
        radii = [r * MM for r in radii_all] + ([0.3 * MM] if half > 0.4 else [])
        s0 = 0.55 * radii[0] / np.sqrt(2.0)
        plan = mesh2d.embed_ogrid(plan, cx * MM, cy * MM, half * MM, n_side_via, radii, s0=s0, n_blend=2 if half > 0.4 else 0, n_inner=1)
    plan = plan.remove(plan.centroids()[:, 1] > 5.0 * MM)
    r_in = (via_r - plating) * MM
    vlist = []
    for cx, cy, half in wins:
        d = dict(cx=cx * MM, cy=cy * MM, r_drill=via_r * MM, r_in=r_in if plating > 0 else 0.0)
        if core not in ("open", "solid"):
            d["k_fill"] = float(core)
        vlist.append(d)
    outline_wall = None
    if plating > 0 and core == "open":
        c = plan.centroids()
        holes = np.zeros(c.shape[0], bool)
        for cx, cy, half in wins:
            holes |= np.hypot(c[:, 0] - cx * MM, c[:, 1] - cy * MM) < r_in
        plan = plan.remove(holes)

        def outline_wall(mid, wins=wins, r_in=r_in):
            """!
            @brief True for the boundary edges that are the board wall (not the wall of a hole).
            @param mid Edge midpoints (B, 2) in m.
            @param wins Via windows (cx, cy, half) in mm.
            @param r_in Inner radius of the barrel in m.
            @return bool (B,).
            """
            ok = np.ones(mid.shape[0], bool)
            for cx, cy, _ in wins:
                ok &= np.hypot(mid[:, 0] - cx * MM, mid[:, 1] - cy * MM) > 1.2 * r_in
            return ok
    return board.Board(plan, 4, board_t=1.6 * MM, k_xy=0.3, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=200.0, h_side=h_side, symmetry=[("y", 5.0 * MM)],
                       vias=vlist, heaters=[(cases.rect(1, 4, 4, 5), 0.5 * power)], outline_wall=outline_wall)
