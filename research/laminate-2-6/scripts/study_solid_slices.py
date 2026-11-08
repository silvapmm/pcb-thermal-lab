#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid_slices.py
@brief Item C of research/laminate-2-6: the 3D solid cuts every insulating gap into 4 equal slabs and does not add the half layer of laminate between the node and the face of a part on bare
       laminate. How many slabs per gap, and the face term, bring it to the reference, and at what cost in unknowns and memory?
@details Part 1: the thick-laminate cases of paper-case-studies (S x S source on a 20 mm board, two layers, h = 1e3, bare and pad), `solid3d.solve_steady` with n_diel = 4, 8, 16, 32 at the cell
         given (default 0.25 mm) against (a) the independent resolved solver of paper-case-studies (`reference_3d` at the SAME pixel and the same number of sub-slabs: they must agree to
         0.01 K once the solid's missing face term is added), (b) the extrapolated reference on record (README 16.4) and equation 50. The pixel error of the cell is printed apart: the
         independent solver at the same pixel with many slabs is the "slab limit at this pixel".
         Part 2: the cost of the proposed rule n_gap = clip(ceil(d / 0.2 mm), 4, 16) on the shipped typical stack-ups (pcbthermal/data/stackups.json) and on the thick cases: slabs, unknowns
         at a given cell and board, and the estimate of the memory guard for the same count.
         Run (repository root, light: at most 1.6 GB at 16 slabs on the 20 mm board; the 32-slab row is skipped unless --heavy): .venv/bin/python research/laminate-2-6/scripts/study_solid_slices.py
"""

import json
import math
import sys

import _boot26

import s2board as B
import study_thick_laminate as S2

CELL = 0.25
T_CU = S2.T_CU


def solid_rprime(c, pad, cell, n_diel, face_term):
    """!
    @brief R' of the 3D solid of a thick-laminate case.
    @param c A case.
    @param pad True for the pad board.
    @param cell Cell in mm.
    @param n_diel Slabs per gap.
    @param face_term True to add the half layer of laminate between the node and the face over bare laminate (the FVM and FDM add it; the 3D solid of 2.5.x did not, the 2.6.0 one does in its own read-out, and then nothing is added here).
    @return Tuple (R' in K/W, unknowns, seconds).
    """
    import time
    from pcbthermal import analysis, solid3d
    p = B.problem_of(c, pad)
    t0 = time.time()
    n = solid3d.unknowns(p, cell, n_diel)[0]
    res = solid3d.solve_steady(p, cell, n_diel)
    dt = time.time() - t0
    mean_src = analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient
    r = mean_src / 4.0 - 1.0 / (c["h"] * (c["W"] * 1e-3) ** 2)
    # 2.6.0 (feature/solid3d-slabs-by-thickness): the solid's own read-out already carries the half-layer face term (arrays face_mean), so adding it again would count it twice
    if face_term and not pad and "face_mean" not in res.arrays:
        r += (T_CU / 2.0) / c["kz"] / (c["S"] * 1e-3) ** 2         # per watt of the source: q'' t_cu / (2 k_z) / q
    return r, n, dt


def rule_slabs(d, per_mm=5.0, lo=4, hi=16):
    """!
    @brief The proposed number of slabs of a gap.
    @param d Gap thickness in m.
    @param per_mm Slabs per millimetre (0.2 mm slabs: 5).
    @param lo Fewest slabs.
    @param hi Most slabs.
    @return int.
    """
    return int(min(hi, max(lo, math.ceil(d * 1e3 * per_mm - 1e-9))))


def part1(heavy):
    """!
    @brief The slab sweep on the thick cases.
    @param heavy True to add 32 slabs.
    @return list of row dicts.
    """
    rows = []
    ns = (4, 8, 16) + ((32,) if heavy else ())
    print("Part 1: S, t, board | n | solid R' (+face term on bare) | independent same pixel | solid vs same pixel % | vs extrapolated/eq.50 %  | unknowns, s")
    for S, t in ((2.0, 1.6), (2.0, 3.2), (5.0, 1.6), (5.0, 3.2)):
        c = B.case(S, t)
        for pad in (False, True):
            ref, src = B.reference(c, pad)
            for n in ns:
                r, u, dt = solid_rprime(c, pad, CELL, n, True)
                same = S2.reference_3d(c, pad, px_div=int(round(S / CELL)), n_sub=n)       # independent solver, same pixel and slabs, with its own face term
                row = dict(S=S, t=t, pad=pad, n=n, R=r, same_pixel=same, ref=ref, unknowns=u, sec=dt)
                rows.append(row)
                print(f"  S{S:g} t{t:g} {'pad ' if pad else 'bare'} n{n:<3d} {r:9.3f} {same:9.3f}  {100 * (r / same - 1):+6.2f}  "
                      f"{('%+7.2f' % (100 * (r / ref - 1))) if ref else '   n/a'}  ({src if ref else 'none'})  {u}, {dt:.1f} s", flush=True)
    return rows


def part2():
    """!
    @brief Slabs, unknowns and memory of the rule on the shipped advanced stack-ups (templates of pcbthermal/data/stackups.json, 0.5 oz and 1 oz inner copper).
    @return list of row dicts.
    """
    from pcbthermal import Problem, memory
    rows = []
    cell, w, h = 1.0, 100.0, 80.0
    cells = (w / cell) * (h / cell)
    print("Part 2: stack-up | gaps (um) | slabs per gap 4 / rule | node slabs | unknowns x | memory guard GB (4 -> rule), board 100 x 80 mm, 1 mm cell")
    for layers in (2, 4, 6, 8, 10):
        for oz in (0.5, 1):
            p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=1.6, copper_um=35.0)
            p.board.template_inner_oz = oz
            p.board.dielectrics = p.board.dielectrics or []
            try:
                p.board.apply_template()
            except Exception as e:                                     # 2 layers: a simple board has no gaps list
                print("   ", layers, oz, "template:", e)
            gaps = [float(g) for g in p.board.gap_thicknesses()]
            n_rule = [rule_slabs(g) for g in gaps]
            ns4, nsr = layers + 4 * len(gaps), layers + sum(n_rule)
            m4 = memory.estimate_bytes("solid3d", ns4 * cells, cells, base=0.0) / 1e9
            mr = memory.estimate_bytes("solid3d", nsr * cells, cells, base=0.0) / 1e9
            rows.append(dict(layers=layers, inner_oz=oz, gaps_um=[g * 1e6 for g in gaps], n_rule=n_rule, slabs_4=ns4, slabs_rule=nsr, ratio=nsr / ns4, gb_4=m4, gb_rule=mr))
            print(f"  {layers} L, {oz} oz: gaps {[round(g * 1e6) for g in gaps]} -> {n_rule}; slabs {ns4} -> {nsr} (x{nsr / ns4:.2f}); memory {m4:.2f} -> {mr:.2f} GB", flush=True)
    return rows


def main(argv=None):
    """!
    @brief Run both parts.
    @param argv Command line (--heavy adds 32 slabs).
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    out = {"part1": [] if "--part2" in argv else part1("--heavy" in argv), "part2": part2()}
    (_boot26.OUT / "study_solid_slices.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
