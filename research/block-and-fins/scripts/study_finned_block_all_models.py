#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_finned_block_all_models.py
@brief A finned metal block in every model (the table "D. Finned metal block" of the program's `docs/validation.md` section 12), and how much the fin ratio applied
       to the sides of the block's base plate adds.

@details The board is the one of `tests/test_heatsink_part.py`: 60 x 40 mm, two layers with copper from 1 to 59 / 1 to 39 mm on both, a 3 W part of 10 x 10 mm on the top,
         an aluminium block of 40 x 30 mm and 3 mm on the bottom face through 5e-5 m2K/W, typed 10 W/m2K on both faces. Four blocks: plain, fins 15 x 1.5 mm at 8 and
         12 mm pitch, fins 30 x 1.5 mm at 8 mm pitch. The rise of the hottest point is printed for the FVM, FDM, 3D solid, Lumped and Analytic.

         Second table: the program multiplies the coefficient of the **sides** of the base plate by the fin ratio too (`blocks.extra_layers`: `h_tot (A c + t L_edge)`,
         with `h_tot = h_face x fin_ratio + h_extra`; the 3D solid does the same). The fins stand on the base face, not on the sides, so the sides of the plate should
         see `h_face + h_extra`. The FVM is re-run on a copy of `blocks.extra_layers` (in memory, the program is not changed) with the sides at `h_face + h_extra`,
         to measure what that choice is worth.

Usage: .venv/bin/python research/block-and-fins/scripts/study_finned_block_all_models.py [cell_mm]   (default 1 mm; about 20 s)
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem, analytic, blocks, fdm, fvm, lumped, solid3d          # noqa: E402

BLOCKS = (("plain plate 3 mm", None), ("fins 15 × 1.5 mm, pitch 8 mm", (15.0, 1.5, 8.0)),
          ("fins 15 × 1.5 mm, pitch 12 mm", (15.0, 1.5, 12.0)), ("fins 30 × 1.5 mm, pitch 8 mm", (30.0, 1.5, 8.0)))


def board(fins=None):
    """!
    @brief The 60 x 40 mm two-layer board of `tests/test_heatsink_part.py` with an aluminium block of 3 mm on the bottom face.
    @param fins None or (height, thickness, pitch) in mm.
    @return Problem.
    """
    p = Problem.new(60, 40, 2)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 10.0, 10.0
    p.add_zone(1, rect=(1, 1, 59, 39))
    p.add_zone(2, rect=(1, 1, 59, 39))
    p.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="U1")
    kw = {} if fins is None else dict(fin_height_mm=fins[0], fin_thickness_mm=fins[1], fin_pitch_mm=fins[2])
    p.add_heatsink(2, 0.0, rect=(10, 5, 50, 35), thickness_mm=3.0, k=204.0, contact_r=5e-5, **kw)
    return p


def sides_without_fins(original):
    """!
    @brief Wrap `blocks.extra_layers` so that the sides of a block lose heat with `h_face + h_extra` instead of `h_face x fin_ratio + h_extra`.
    @details The exposed base keeps the fin ratio. The side length inside every cell is recomputed as in `blocks.extra_layers` (coverage differences with the four
             neighbours); valid for one block per face, as here.
    @param original The function `blocks.extra_layers` of the program.
    @return A function with the same signature.
    """
    def wrapped(problem, cover, area, fill, dx, dy):
        """!
        @brief `blocks.extra_layers` with the side coefficient of every block taken without the fin ratio.
        @param problem A Problem.
        @param cover Coverage function cover(polygon, samples).
        @param area Area of every cell in m2.
        @param fill Copper fill of the board layers.
        @param dx Cell size along x in m.
        @param dy Cell size along y in m.
        @return The list of dicts of `blocks.extra_layers`, with g_amb changed.
        """
        out = original(problem, cover, area, fill, dx, dy)
        b = problem.board
        for lay in out:
            h_face = b.h_top if lay["face"] == 0 else b.h_bottom
            for s in problem.heatsinks:
                if not s.is_block():
                    continue
                c = cover(s.polygon, 4)
                pad = np.pad(c, 1)
                side = np.zeros_like(c)
                for axis, length in ((1, dy), (0, dx)):
                    for sgn in (-1, 1):
                        side += length * np.maximum(c - np.roll(pad, sgn, axis=axis)[1:-1, 1:-1], 0.0)
                take = c > 0
                h_tot = blocks.exposed_h(s, h_face)
                lay["g_amb"] = np.where(take, h_tot * area * c + (h_face + s.h_extra) * s.thickness * side, lay["g_amb"])
        return out
    return wrapped


def main(cell=1.0):
    """!
    @brief Print the table of the five models and the effect of the side coefficient.
    @param cell Cell size in mm.
    """
    print(f"Rise of the hottest point (K), {cell:g} mm cells")
    print("| Block | Fin ratio at 10 W/m²K | FVM | FDM | 3D solid | Lumped | Analytic |")
    print("| :-- | --: | --: | --: | --: | --: | --: |")
    fvm_rise = {}
    for name, fins in BLOCKS:
        p = board(fins)
        r = {m: mod.solve_steady(p, cell_mm=cell).delta_t for m, mod in (("fvm", fvm), ("fdm", fdm), ("solid3d", solid3d), ("lumped", lumped), ("analytic", analytic))}
        fvm_rise[name] = r["fvm"]
        ratio = blocks.fin_ratio(10.0, p.heatsinks[0])
        print(f"| {name} | {ratio:.1f} | {r['fvm']:.1f} | {r['fdm']:.1f} | {r['solid3d']:.1f} | {r['lumped']:.1f} | {r['analytic']:.1f} |", flush=True)
        print(f"|   (against the FVM) | | | {100 * (r['fdm'] / r['fvm'] - 1):+.1f} % | {100 * (r['solid3d'] / r['fvm'] - 1):+.1f} % | "
              f"{100 * (r['lumped'] / r['fvm'] - 1):+.1f} % | {100 * (r['analytic'] / r['fvm'] - 1):+.1f} % |")
    print("\nFVM with the sides of the base plate at h_face + h_extra (no fin ratio on the sides)")
    print("| Block | sides x fin ratio (program) | sides without fins | difference |")
    print("| :-- | --: | --: | --: |")
    original = blocks.extra_layers
    blocks.extra_layers = sides_without_fins(original)
    try:
        for name, fins in BLOCKS:
            alt = fvm.solve_steady(board(fins), cell_mm=cell).delta_t
            print(f"| {name} | {fvm_rise[name]:.1f} | {alt:.1f} | {100 * (alt / fvm_rise[name] - 1):+.1f} % |", flush=True)
    finally:
        blocks.extra_layers = original


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0)
