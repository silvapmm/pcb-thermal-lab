#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference.py
@brief The independent 3D reference of the edge study: hottest rise of the uniform two- and four-layer boards of research/analytic-edge-spatial with the side film on every slab, converged in the
       sub-slabs and in the cell, and its own error.
@details Solver: research/analytic-edge-spatial/lib/layered3d_side.py (imports nothing from pcbthermal). For every case: R(1 mm, 8), R(1 mm, 16), R(0.5 mm, 8); the reference used by the other
         studies is R(1 mm, 16) x R(0.5 mm, 8) / R(1 mm, 8), the product of the two measured corrections (sub-slabs 8 -> 16, cell 1 -> 0.5 mm). A subset also gets R(0.5, 16) to test that
         product. Boards 60 x 40 mm, faces 10 W/m2K, a 10 mm, 2 W part, full 35 um copper on every layer, FR-4 0.9 / 0.3 W/mK.
         Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_reference.py [--quick] [--small] [--four]; writes out/refs.json (60 x 40 mm) or out/refs30.json (30 x 20 mm, reference R(0.25 mm, 4) x R(0.5 mm, 16) / R(0.5 mm, 4)) (cached: a case already there is not repeated).
"""

import json
import sys
import time

import _bootband

import cases

HS = [10.0, 50.0, 200.0, 500.0, 2000.0]
THICK = [0.8, 1.6, 3.2]


def grid(layers_list=(2,), quick=False, size=(60, 40)):
    """!
    @brief The cases (w, h, layers, t, h_side, pos).
    @param layers_list Layer counts.
    @param quick True: a short list.
    @param size Board (width, height) in mm.
    @return List of tuples.
    """
    out = []
    for lay in layers_list:
        for t in ([1.6, 3.2] if quick else THICK):
            for hs in ([200.0, 2000.0] if quick else HS):
                for pos in ("corner", "centre"):
                    out.append((size[0], size[1], lay, t, hs, pos))
    return out


def key(c):
    """!
    @brief Dictionary key of a case.
    @param c Tuple.
    @return str
    """
    return "|".join(str(x) for x in c)


def main(argv=None):
    """!
    @brief Compute the references and store them.
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    small = "--small" in argv                     # 30 x 20 mm board, converged to 0.25 mm in the cell
    path = _bootband.OUT / (("refs30" if small else "refs") + ("_4L" if "--four" in argv else "") + ".json")
    refs = json.loads(path.read_text()) if path.exists() else {}
    layers = (4,) if "--four" in argv else (2,)
    for c in grid(layers, "--quick" in argv, (30, 20) if small else (60, 40)):
        if "--four" in argv and not (c[3] in (1.6, 3.2) and c[4] in (50.0, 200.0, 500.0) and c[5] == "corner"):
            continue                                  # the four-layer subset
        k = key(c)
        if k in refs:
            continue
        p, xy = cases.board(*c)
        t0 = time.time()
        if "--four" in argv:
            # four layers (heavier 3D): R(0.5 mm, 8 sub-slabs) corrected for the sub-slabs by R(1 mm, 16) / R(1 mm, 8); accurate to about 1 %
            r058 = cases.ref3d(p, xy, 0.5, sub=8)
            r18 = cases.ref3d(p, xy, 1.0, sub=8)
            r116 = cases.ref3d(p, xy, 1.0, sub=16)
            refs[k] = dict(r05_8=r058, r1_8=r18, r1_16=r116, ref=r058 * r116 / r18)
        elif small:
            # 30 x 20 mm: R(0.25 mm, 4 sub-slabs) corrected for the sub-slabs by R(0.5 mm, 16) / R(0.5 mm, 4)
            r025 = cases.ref3d(p, xy, 0.25, sub=4)
            r054 = cases.ref3d(p, xy, 0.5, sub=4)
            r0516 = cases.ref3d(p, xy, 0.5, sub=16)
            refs[k] = dict(r025_4=r025, r05_4=r054, r05_16=r0516, ref=r025 * r0516 / r054)
        else:
            r18 = cases.ref3d(p, xy, 1.0, sub=8)
            r116 = cases.ref3d(p, xy, 1.0, sub=16)
            r058 = cases.ref3d(p, xy, 0.5, sub=8)
            refs[k] = dict(r1_8=r18, r1_16=r116, r05_8=r058, ref=r116 * r058 / r18)
        path.write_text(json.dumps(refs, indent=1))
        print(k, {a: round(b, 3) for a, b in refs[k].items()}, f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
