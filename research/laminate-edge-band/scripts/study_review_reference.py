#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_reference.py
@brief Review: how far is the study's 3D reference from converged? The graded-mesh solver lib/graded3d.py at 16, 32 and 64 (48 on 0.8 mm) laminate sub-slabs and at a finer in-plane mesh,
       extrapolated in the sub-slabs (Richardson with the observed ratio), for eight cases of the 30 x 20 mm board.
@details Writes out/refs_review.json (the converged rise per case, keyed like out/refs30.json) and prints the bias of the study's reference. About 3 min, peak below 1 GB (AMG).
         Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_review_reference.py
"""

import json

import _bootband

import graded3d

CASES = [(3.2, 200.0, "corner"), (3.2, 200.0, "centre"), (3.2, 500.0, "corner"), (3.2, 2000.0, "corner"), (3.2, 2000.0, "centre"), (1.6, 200.0, "corner"),
         (0.8, 200.0, "corner"), (0.8, 2000.0, "corner")]


def converged(t, hs, pos):
    """!
    @brief The rise of one case at three sub-slab counts and a finer in-plane mesh, and the extrapolated value.
    @param t Thickness in mm.
    @param hs Edge coefficient in W/m2K.
    @param pos "corner" or "centre".
    @return dict z16, z32, zN, xy (change of the finer in-plane mesh at 32 sub-slabs), ref.
    """
    nz3 = 48 if t < 1 else 64
    z16 = graded3d.case(t, hs, pos, nz_lam=16)["rise"]
    z32 = graded3d.case(t, hs, pos, nz_lam=32)["rise"]
    z3 = graded3d.case(t, hs, pos, nz_lam=nz3)["rise"]
    f = graded3d.case(t, hs, pos, nz_lam=32, h_max=2.5e-4, h_min=1e-5)
    if not abs(f["balance"] - 1.0) < 1e-6:            # the AMG did not converge once (quarter board, 200 W/m2K): the same refinement with a 20 um first cell
        f = graded3d.case(t, hs, pos, nz_lam=32, h_max=2.5e-4, h_min=2e-5)
    fine = f["rise"]
    rho = (z16 - z32) / (z32 - z3)
    tail = (z32 - z3) / (rho - 1.0) if nz3 == 64 else 0.6 * (z32 - z3)     # remaining sub-slab change after the last level
    xy = fine - z32
    return dict(z16=z16, z32=z32, zN=z3, xy=xy, ref=z3 - tail + xy)


def main():
    """!
    @brief Run the cases, store and print.
    @return None
    """
    study = json.loads((_bootband.OUT / "refs30.json").read_text())
    out = {}
    for t, hs, pos in CASES:
        k = f"30|20|2|{t}|{hs}|{pos}"
        r = converged(t, hs, pos)
        out[k] = r["ref"]
        print(f"{k}: z16 {r['z16']:.3f} z32 {r['z32']:.3f} zN {r['zN']:.3f} xy {r['xy']:+.4f} -> {r['ref']:.3f} K; study reference {study[k]['ref']:.3f} "
              f"({100 * (study[k]['ref'] / r['ref'] - 1):+.2f} %)", flush=True)
    (_bootband.OUT / "refs_review.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
