#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_face_term.py
@brief The read-out under a part over absent thick copper in the 3D solid (the review of `feature/solid3d-copper-slabs`): the column, the outer slab, the face term and their sum, against the FVM.
@details Question: with several copper slabs, the heat of a part on a thick outer layer enters the outer slab while the reported layer temperature is the column (the mean of the
         slabs). Which face term turns that column into the face temperature under a part over absent copper? In 1D the face is q t / (2 k) above the column mean whatever the slab
         count; a term of q t / (2 n k) (the half outer slab alone) leaves out the (n - 1) q t / (2 n k) by which the outer slab is above the mean. The board: 40 x 40 mm, two
         layers, the top bare (no copper drawn), the bottom full, a 4 x 4 mm part of 0.5 W at the centre, films of 10 W/m2K, 1 mm cell; copper 35, 140 and 420 um (the gap kept).

             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/study_face_term.py --tree <checkout>

         Printed per thickness: slabs of the top layer, the column under the part (degC), the outer slab (degC, the tree before the branch has one slab, so the column), the face term (K),
         column + term (the read-out of the program under the part, degC), outer slab + half outer slab of laminate (the face the solid resolves, degC), and the FVM column, term and sum.
"""

import argparse
import sys
from pathlib import Path


def board(Problem, um):
    """!
    @brief The board of the question.
    @param Problem The Problem class of the tree.
    @param um Copper thickness of both layers, um.
    @return Problem.
    """
    p = Problem.new(40, 40, layers=2, thickness_mm=1.6 + 2 * (um - 35) * 1e-3, copper_um=um)
    p.board.h_top = p.board.h_bottom = 10.0
    p.add_full_copper(layers=[2])                                # bottom full, top bare: the part sits over absent copper
    p.add_heater(1, 0.5, rect=(18, 18, 22, 22), name="U")
    return p


def main(argv=None):
    """!
    @brief Run the three thicknesses on one tree and print one line each.
    @param argv Arguments (default sys.argv[1:]).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tree", required=True, help="checkout whose pcbthermal is measured")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(a.tree).resolve()))
    from pcbthermal import Problem, fvm, solid3d
    for um in (35, 140, 420):
        p = board(Problem, um)
        r = solid3d.solve_steady(p, cell_mm=1.0)
        net = solid3d.Solid(p, 1.0)
        th, _ = net.solve()
        cs = getattr(net, "copper_slabs", [[net.board_slab[0]]])[0]
        i = j = 20
        col = float(r.T[0, i, j])
        outer = float(th[cs[0], i, j]) + p.board.ambient
        term = float(r.arrays["face_peak"][0, i, j])
        sl = net.slabs[cs[0]]
        half = float(net.Q.reshape(th.shape)[cs[0], i, j] * sl["dz"][i, j] / 2.0 / (sl["kz"][i, j] * net.area_b[i, j]))
        f = fvm.solve_steady(p, cell_mm=1.0)
        ft = float(f.arrays["face_peak"][0, i, j])
        print(f"{um:4d} um  slabs {len(cs)}  column {col:.3f}  outer slab {outer:.3f}  term {term:.3f}  column+term {col + term:.3f}  "
              f"outer+half slab {outer + half:.3f}  |  FVM column {float(f.T[0, i, j]):.3f}  term {ft:.3f}  sum {float(f.T[0, i, j]) + ft:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
