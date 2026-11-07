#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_reference.py
@brief Review: do the program's swing, the author's reference and the estimator E3 hold against an independent 3D reference of the rectangular board, on the author's sweep
       and on cases the author did not test (heater on an inner or bottom layer, no copper under the part, vias, an elongated part, a part off the centre, computed h, the FDM)?

@details The reference is lib/review_rect3d.py (written by the reviewer; Cartesian 3D finite volumes of the real rectangle and part, frequency domain, hottest footprint cell),
which shares no code with lib/axisym_stack.py. For every board the program's step responses (FVM at the author's cell side / 4 at most 1 mm, FVM at 2 mm (the cell the
application uses for the decision, `api._step_response`: max(cell, 2 mm)), FDM at side / 4) give the oscillation of `profiles.decide`; E3 is the author's
`impedance.square_swing` applied as the proposal would apply it (the top-sheet formula with the board's stack, a disc of the part's area). Writes out/review_sample.json and
out/review_cases.json and out/review_example.json, read by study_review_tables.py, which prints the tables of README section 9. Run from the repository root (about 10 minutes, peak memory about 1.5 GB):
`QT_QPA_PLATFORM=offscreen .venv/bin/python research/fast-wave-oscillation/scripts/study_review_reference.py [sample|cases|bare|example|all]`.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)

import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
import impedance as I                                                # noqa: E402
import review_rect3d as R                                            # noqa: E402
from pcbthermal import api, profiles                                 # noqa: E402
from pcbthermal.model import Problem, SquareWave                     # noqa: E402

OUT = os.path.join(HERE, "..", "out")
FREQS = [0.1, 0.3, 1, 3, 10, 20, 50, 100, 300, 1000, 3000]
DUTIES = [0.1, 0.3, 0.5, 0.9]
W, H = 60.0, 40.0


def program_oscillations(problem, cells, models=("fvm",)):
    """!
    @brief Step responses of the program for one board, to be reused for every wave.
    @param problem Problem with one heater (the wave is set later).
    @param cells Cells in mm, one per response.
    @param models Model per response ("fvm" or "fdm").
    @return List of StepResponse.
    """
    out = []
    for cell, m in zip(cells, models):
        out.append(profiles.step_response_fvm(problem, cell) if m == "fvm" else profiles.step_response_fdm(problem, cell))
    return out


def decision_osc(problem, resp, f, duty, heater=0):
    """!
    @brief The oscillation that profiles.decide uses, per watt of on-power, for one wave of one heater.
    @param problem Problem.
    @param resp StepResponse.
    @param f Frequency (Hz).
    @param duty Duty.
    @param heater Heater index.
    @return K/W.
    """
    problem.heaters[heater].profile = SquareWave(p_on=1.0, period=1.0 / f, duty=duty)
    return float(profiles.decide(problem, resp, 1.0)[heater].oscillation)


def e3(layers, side_x, side_y, h_top, h_bottom, f, duty, thickness=1.6e-3):
    """!
    @brief E3 as the proposal applies it: the top-sheet formula, the board's stack, a disc of the part's area.
    @param layers Copper layers.
    @param side_x Part side along x (m).
    @param side_y Part side along y (m).
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param f Frequency (Hz).
    @param duty Duty.
    @param thickness Board thickness (m).
    @return K/W.
    """
    st = A.Stack(layers=layers, thickness=thickness)
    return I.square_swing(st, 1.0 / f, duty, float(np.sqrt(side_x * side_y / np.pi)), h_top, h_bottom)


def centred(side_x, side_y=None):
    """!
    @brief The rectangle of a part centred on the 60 x 40 mm board, in mm.
    @param side_x Side along x (mm).
    @param side_y Side along y (mm), default side_x.
    @return Tuple (x0, y0, x1, y1).
    """
    side_y = side_x if side_y is None else side_y
    return (0.5 * (W - side_x), 0.5 * (H - side_y), 0.5 * (W + side_x), 0.5 * (H + side_y))


def sample():
    """!
    @brief The author's sweep on 12 boards against the reviewer's reference (every frequency and duty of each board).
    @return List of records.
    """
    author = {(r["layers"], r["side"], r["h"], r["f"], r["duty"]): r for r in json.load(open(os.path.join(OUT, "sweep.json"))) if not r["bare"]}
    boards = [(L, s, 10.0) for L in (1, 2, 4) for s in (2.0, 5.0, 10.0)] + [(2, 2.0, 30.0), (2, 10.0, 30.0), (4, 5.0, 30.0)]
    out = []
    t0 = time.time()
    for L, side, h in boards:
        rect = centred(side)
        p = Problem.new(W, H, L, 1.6, h_top=h, h_bottom=h, h_side=0.0).add_full_copper()
        p.add_heater(1, 1.0, rect=rect, name="u", profile=SquareWave(p_on=1.0, period=1.0, duty=0.5))
        cell = min(1.0, side / 4.0)
        r_fvm, r_fvm2, r_fdm = program_oscillations(p, (cell, 2.0, cell), ("fvm", "fvm", "fdm"))
        ref = R.Reference(R.Board(layers=L, h_top=h, h_bottom=h), R.Case(part=tuple(v * 1e-3 for v in rect)), quarter=True)
        rs = R.Response(ref)
        for f in FREQS:
            for duty in DUTIES:
                a = author.get((L, side, h, f, duty), {})
                out.append({"layers": L, "side": side, "h": h, "f": f, "duty": duty, "ref": rs.swing(1.0 / f, duty),
                            "author_ref": a.get("ref_center"), "fvm": decision_osc(p, r_fvm, f, duty), "fvm_2mm": decision_osc(p, r_fvm2, f, duty),
                            "fdm": decision_osc(p, r_fdm, f, duty), "e3": e3(L, side * 1e-3, side * 1e-3, h, h, f, duty)})
        print(f"sample L={L} side={side} h={h} unknowns={ref.n} ({time.time() - t0:.0f} s)", flush=True)
    return out


def new_cases(only_bare=False):
    """!
    @brief Cases the author did not test, each against the reviewer's reference.
    @param only_bare True: only the cases with the top copper removed under the part (run again with a thin surface cell, see review_rect3d.Reference top_first).
    @return List of records.
    """
    cases = []
    mm = 1e-3
    # (label, layers, heater layer (1-based), part rect in mm, top copper removed rects (mm), vias (mm), quarter, h_top, h_bottom)
    r10 = centred(10.0)
    r5 = centred(5.0)
    hole = (r10[0] - 1.0, r10[1] - 1.0, r10[2] + 1.0, r10[3] + 1.0)
    vias = [(30.0 + dx, 20.0 + dy) for dx in (-3.75, -1.25, 1.25, 3.75) for dy in (-3.75, -1.25, 1.25, 3.75)]
    spec = [
        ("inner layer 2 of 4, 10 mm", 4, 2, r10, None, [], True),
        ("inner layer 2 of 4, 5 mm", 4, 2, r5, None, [], True),
        ("bottom layer of 2, 10 mm", 2, 2, r10, None, [], True),
        ("no top copper under the part (1 mm clearance), 10 mm", 2, 1, r10, hole, [], True),
        ("no top copper at all, 10 mm", 2, 1, r10, (0.0, 0.0, W, H), [], True),
        ("16 vias under the part, 10 mm, 2 layers", 2, 1, r10, None, vias, True),
        ("16 vias under the part, 10 mm, 4 layers", 4, 1, r10, None, vias, True),
        ("elongated 2 x 10 mm", 2, 1, centred(2.0, 10.0), None, [], True),
        ("off centre, 10 mm at (8, 8)", 2, 1, (8.0, 8.0, 18.0, 18.0), None, [], False),
        ("near the corner, 5 mm at (1, 1)", 2, 1, (1.0, 1.0, 6.0, 6.0), None, [], False),
    ]
    t0 = time.time()
    for label, L, layer, rect, removed, vs, quarter in spec:
        if only_bare and removed is None:
            continue
        p = Problem.new(W, H, L, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
        for lay in range(1, L + 1):
            if lay == 1 and removed is not None:
                x0, y0, x1, y1 = removed
                for z in ((0, 0, W, y0), (0, y1, W, H), (0, y0, x0, y1), (x1, y0, W, y1)):
                    if z[2] > z[0] and z[3] > z[1]:
                        p.add_zone(1, rect=z)
            else:
                p.add_zone(lay, rect=(0, 0, W, H))
        for (vx, vy) in vs:
            p.add_via(vx, vy, 0.3)
        p.add_heater(layer, 1.0, rect=rect, name="u", profile=SquareWave(p_on=1.0, period=1.0, duty=0.5))
        side = min(rect[2] - rect[0], rect[3] - rect[1])
        cell = min(1.0, side / 4.0)
        r_fvm, r_fdm = program_oscillations(p, (cell, cell), ("fvm", "fdm"))
        nc = [(0, tuple(v * mm for v in removed))] if removed is not None else []
        case = R.Case(part=tuple(v * mm for v in rect), layer=layer - 1, no_copper=nc, vias=[(x * mm, y * mm) for x, y in vs])
        # A part on bare laminate is read at the laminate surface: the surface cell must be thin (0.05 um, graded)
        ref = R.Reference(R.Board(layers=L), case, quarter=quarter, top_first=0.05e-6 if removed is not None else None)
        rs = R.Response(ref)
        for f in FREQS:
            for duty in (0.3, 0.5):
                cases.append({"case": label, "f": f, "duty": duty, "ref": rs.swing(1.0 / f, duty), "fvm": decision_osc(p, r_fvm, f, duty),
                              "fdm": decision_osc(p, r_fdm, f, duty), "e3": e3(L, (rect[2] - rect[0]) * mm, (rect[3] - rect[1]) * mm, 10.0, 10.0, f, duty)})
        print(f"case {label}: unknowns {ref.n} ({time.time() - t0:.0f} s)", flush=True)
    if only_bare:
        return cases
    # Computed h: the program holds the steady coefficients in the time run (api: effective_problem with manual h), so the reference takes the same numbers
    for power in (1.0, 10.0):
        p = Problem.new(W, H, 2, 1.6, h_side=0.0).add_full_copper()
        p.board.h_mode = "computed"
        p.add_heater(1, power, rect=r10, name="u")
        sim = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=1.0))
        ht, hb = sim.h_used["fvm"]
        q = Problem.new(W, H, 2, 1.6, h_top=ht, h_bottom=hb, h_side=0.0).add_full_copper()
        q.add_heater(1, 1.0, rect=r10, name="u", profile=SquareWave(p_on=1.0, period=1.0, duty=0.5))
        r_fvm, r_fdm = program_oscillations(q, (1.0, 1.0), ("fvm", "fdm"))
        rs = R.Response(R.Reference(R.Board(layers=2, h_top=ht, h_bottom=hb), R.Case(part=tuple(v * mm for v in r10)), quarter=True))
        label = f"computed h, {power:g} W steady (h_top {ht:.1f}, h_bottom {hb:.1f})"
        for f in FREQS:
            for duty in (0.3, 0.5):
                cases.append({"case": label, "f": f, "duty": duty, "ref": rs.swing(1.0 / f, duty), "fvm": decision_osc(q, r_fvm, f, duty),
                              "fdm": decision_osc(q, r_fdm, f, duty), "e3": e3(2, 10 * mm, 10 * mm, ht, hb, f, duty)})
        print(f"case {label} ({time.time() - t0:.0f} s)", flush=True)
    return cases


def example_u1():
    """!
    @brief U1 of the example board (4 layers, 9 vias, a bottom heatsink of 30 W/m2K, h 10 / 15, top copper zone 70 x 50 mm) against the reference.
    @return List of records.
    """
    from pcbthermal.examples import example_board
    p = example_board()
    b = p.board
    resp = profiles.step_response_fvm(p, 2.0)
    mm = 1e-3
    zone = p.zones[0].polygon
    zx0, zy0, zx1, zy1 = zone[:, 0].min(), zone[:, 1].min(), zone[:, 0].max(), zone[:, 1].max()
    Wb, Hb = b.width, b.height
    removed = [(0, r) for r in ((0, 0, Wb, zy0), (0, zy1, Wb, Hb), (0, zy0, zx0, zy1), (zx1, zy0, Wb, zy1))]
    hs = p.heatsinks[0].polygon
    case = R.Case(part=tuple(np.r_[p.heaters[0].polygon.min(axis=0), p.heaters[0].polygon.max(axis=0)]), no_copper=removed,
                  vias=[(v.x, v.y) for v in p.vias], bottom_extra=[((hs[:, 0].min(), hs[:, 1].min(), hs[:, 0].max(), hs[:, 1].max()), p.heatsinks[0].h_extra)])
    # A coarser grid (the whole 100 x 80 mm board, four layers): growth 1.8 in the plane and in the laminate keeps it under 2 GB
    ref = R.Reference(R.Board(width=Wb, height=Hb, layers=b.layers, thickness=b.thickness, h_top=b.h_top, h_bottom=b.h_bottom), case,
                      fine=2.0e-3, margin=2.0e-3, growth_xy=1.8, n_cu=3, first=1.5e-6, growth_z=1.8)
    rs = R.Response(ref)
    out = []
    for f in (0.05, 1.0, 10.0, 100.0, 1000.0):
        for duty in (0.3,):
            pk = p.heaters[0]
            pk.profile = SquareWave(p_on=1.0, period=1.0 / f, duty=duty)
            p.heaters[1].profile = None
            osc = float(profiles.decide(p, resp, 1.0)[0].oscillation)
            out.append({"case": "example board U1 (h_side 10 not in the reference)", "f": f, "duty": duty, "ref": rs.swing(1.0 / f, duty), "fvm": osc, "fdm": None,
                        "e3": I.square_swing(A.Stack(layers=4), 1.0 / f, duty, float(np.sqrt(1e-4 / np.pi)), b.h_top, b.h_bottom)})
    print(f"example U1: unknowns {ref.n}", flush=True)
    return out


def main():
    """!
    @brief Run and save.
    @return None.
    """
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    if what in ("sample", "all"):
        json.dump(sample(), open(os.path.join(OUT, "review_sample.json"), "w"))
    if what in ("cases", "all"):
        json.dump(new_cases(), open(os.path.join(OUT, "review_cases.json"), "w"))
    if what in ("bare", "all"):
        json.dump(new_cases(only_bare=True), open(os.path.join(OUT, "review_bare.json"), "w"))
    if what in ("example", "all"):
        json.dump(example_u1(), open(os.path.join(OUT, "review_example.json"), "w"))


if __name__ == "__main__":
    main()
