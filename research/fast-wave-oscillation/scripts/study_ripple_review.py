#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_ripple_review.py
@brief Review of fix/fast-wave-ripple: does the program's closed form (pcbthermal/stackimpedance.py) and its use in profiles.decide and run_windows hold against the reviewer's
       independent Cartesian 3D reference (lib/review_rect3d.py), on the saved cases of this folder and on new ones (tables, vias by density, copper over half the part, other
       layers, 10 kHz convergence), and what do the Lumped and Analytic step responses, two neighbours and the finer response cell do?

@details The program is imported from the tree named by the environment variable PCBT_TREE (a checkout of fix/fast-wave-ripple or a later tree with pcbthermal/stackimpedance.py;
default the repository root of this folder). Parts (argument): ``saved`` (the closed form on the 528 + 264 saved cases of out/review_sample.json and out/review_cases.json, and the
3168 decisions with the floor), ``table371`` (node / closed form, docs/validation.md 37.1), ``fresh`` (6 new boards x 18 waves against new 3D runs, about 15 minutes, 2.2 GB),
``tables``, ``vias``, ``partial``, ``conv`` (new 3D runs, about 20 minutes, 2.5 GB), ``models`` (the Lumped and Analytic step responses and runs), ``cross`` (the closed-form wave of a
neighbour), ``cell`` (cost of api.response_cell_mm on a 100 x 80 mm board), ``envelope`` (the extremes of the ripple against the reference, one 3D run). Run from the repository root:
`PCBT_TREE=<tree> QT_QPA_PLATFORM=offscreen .venv/bin/python research/fast-wave-oscillation/scripts/study_ripple_review.py saved table371 models cross cell [fresh tables vias partial conv]`.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.environ.get("PCBT_TREE", ROOT))

import numpy as np                                                   # noqa: E402
from scipy.special import iv, kv                                     # noqa: E402

import review_rect3d as R                                            # noqa: E402
from pcbthermal import api, profiles, stackimpedance as S           # noqa: E402
from pcbthermal.model import Problem, SquareWave, TableProfile       # noqa: E402

OUT = os.path.join(HERE, "..", "out")
W, H = 60.0, 40.0
MM = 1e-3


def centred(a, b=None):
    """!
    @brief The rectangle of a part centred on the 60 x 40 mm board, in mm.
    @param a Side along x (mm).
    @param b Side along y (mm), default a.
    @return Tuple (x0, y0, x1, y1).
    """
    b = a if b is None else b
    return (30 - a / 2, 20 - b / 2, 30 + a / 2, 20 + b / 2)


def full_board(layers, rect, layer=1, h_top=10.0, h_bottom=10.0, vias=(), profile=None):
    """!
    @brief A full-copper board of the study with one part.
    @param layers Copper layers.
    @param rect Part rectangle in mm.
    @param layer 1-based layer of the part.
    @param h_top Top coefficient (W/m2K).
    @param h_bottom Bottom coefficient (W/m2K).
    @param vias Via centres in mm (drill 0.3 mm).
    @param profile Optional power profile.
    @return Problem.
    """
    p = Problem.new(W, H, layers, 1.6, h_top=h_top, h_bottom=h_bottom, h_side=0.0).add_full_copper()
    for x, y in vias:
        p.add_via(x, y, 0.3)
    p.add_heater(layer, 1.0, rect=rect, name="u", profile=profile)
    return p


def closed(p, f, duty):
    """!
    @brief The program's closed-form swing of a unit square wave, or None where it does not apply.
    @param p Problem.
    @param f Frequency (Hz).
    @param duty Duty.
    @return K/W or None.
    """
    col, _ = S.column_for_heater(p, 0)
    return None if col is None else col.swing(1.0 / f, duty)


def part_saved():
    """!
    @brief The closed form on the saved reference cases and the decisions with the floor.
    """
    smp = json.load(open(os.path.join(OUT, "review_sample.json")))
    boards, rows = {}, []
    for r in smp:
        key = (r["layers"], r["side"], r["h"])
        if key not in boards:
            boards[key] = full_board(r["layers"], centred(r["side"]), h_top=r["h"], h_bottom=r["h"])
        cf = closed(boards[key], r["f"], r["duty"])
        rows.append((key, r["f"], r["duty"], cf / r["ref"], max(r["fvm"], cf), r["ref"]))
    ratios = np.array([x[3] for x in rows])
    print(f"saved sample: {len(rows)} cases, closed form / reference {ratios.min():.3f} to {ratios.max():.3f}, median {np.median(ratios):.3f}")
    powers = np.geomspace(0.03, 30.0, 6)
    wa = sum(1 for x in rows for q in powers if q * x[4] <= 1.0 < q * x[5])
    wr = sum(1 for x in rows for q in powers if q * x[5] <= 1.0 < q * x[4])
    print(f"decisions (budget 1 K, 6 powers 0.03 to 30 W): {len(rows) * len(powers)}, wrong averages {wa}, wrong resolves {wr}")
    r10, r5 = centred(10.0), centred(5.0)
    vias16 = [(30.0 + dx, 20.0 + dy) for dx in (-3.75, -1.25, 1.25, 3.75) for dy in (-3.75, -1.25, 1.25, 3.75)]
    spec = {"inner layer 2 of 4, 10 mm": full_board(4, r10, 2), "inner layer 2 of 4, 5 mm": full_board(4, r5, 2), "bottom layer of 2, 10 mm": full_board(2, r10, 2),
            "16 vias under the part, 10 mm, 2 layers": full_board(2, r10, vias=vias16), "16 vias under the part, 10 mm, 4 layers": full_board(4, r10, vias=vias16),
            "elongated 2 x 10 mm": full_board(2, centred(2.0, 10.0)), "off centre, 10 mm at (8, 8)": full_board(2, (8, 8, 18, 18)),
            "near the corner, 5 mm at (1, 1)": full_board(2, (1, 1, 6, 6)),
            "computed h, 1 W steady (h_top 14.5, h_bottom 10.1)": full_board(2, r10, h_top=14.5, h_bottom=10.1),
            "computed h, 10 W steady (h_top 22.5, h_bottom 15.5)": full_board(2, r10, h_top=22.5, h_bottom=15.5)}
    by = {}
    for r in json.load(open(os.path.join(OUT, "review_cases.json"))):
        if r["case"] in spec:
            by.setdefault(r["case"], []).append((r["f"], closed(spec[r["case"]], r["f"], r["duty"]) / r["ref"]))
    for k, v in by.items():
        a = np.array([x[1] for x in v])
        print(f"  {k}: {a.min():.3f} to {a.max():.3f} (highest at {v[int(a.argmax())][0]} Hz)")


def part_table371():
    """!
    @brief docs/validation.md 37.1: node swing of the decision / closed form, duty 50 %, FVM response at side / 4 (at most 1 mm).
    """
    print("layers, part | 0.1 Hz | 1 | 10 | 100 | 1 kHz")
    for L, side in ((2, 2.0), (2, 10.0), (1, 10.0), (4, 2.0), (4, 10.0)):
        p = full_board(L, centred(side))
        resp = profiles.step_response_fvm(p, min(1.0, side / 4.0))
        row = []
        for f in (0.1, 1.0, 10.0, 100.0, 1000.0):
            w = SquareWave(p_on=1.0, period=1.0 / f, duty=0.5)
            pk, vl = profiles.wave_response(resp, 0, w)
            row.append((pk - vl) / closed(p, f, 0.5))
        print(f"{L}, {side:g} mm | " + " | ".join(f"{x:.2f}" for x in row))


def part_fresh():
    """!
    @brief Six boards the saved cases do not hold, 18 waves each, against new 3D runs.
    """
    boards = [("4 layers, heater on layer 3, 5 mm", 4, 3, centred(5), 10, 10), ("4 layers, heater on the bottom, 10 mm", 4, 4, centred(10), 10, 10),
              ("6 layers, top, 5 mm", 6, 1, centred(5), 10, 10), ("1 layer, 2 mm", 1, 1, centred(2), 10, 10), ("2 layers, 5 mm, h 30 / 10", 2, 1, centred(5), 30, 10),
              ("4 layers, elongated 3 x 8 mm", 4, 1, centred(3, 8), 10, 10)]
    t0 = time.time()
    for lab, L, lay, rect, ht, hb in boards:
        p = full_board(L, rect, lay, ht, hb)
        rs = R.Response(R.Reference(R.Board(layers=L, h_top=ht, h_bottom=hb), R.Case(part=tuple(v * MM for v in rect), layer=lay - 1), quarter=True))
        rr = [closed(p, f, d) / rs.swing(1.0 / f, d) for f in (0.1, 1, 10, 100, 1000, 10000) for d in (0.1, 0.5, 0.9)]
        print(f"fresh {lab}: {min(rr):.3f} to {max(rr):.3f} ({time.time() - t0:.0f} s)", flush=True)


def _ref_profile_swing(rs, tab, n=16384):
    """!
    @brief The reference swing of the hottest footprint cell for a power table (the harmonic sum of the reference's transfer function with the table's coefficients).
    @param rs review_rect3d.Response.
    @param tab TableProfile.
    @param n Samples per period.
    @return Swing in K.
    """
    k = np.arange(1, n // 2)
    c = S.profile_coefficients(tab, n)
    hk = rs.H(k / tab.period)
    spec = np.zeros((n, hk.shape[1]), dtype=complex)
    spec[1:n // 2] = hk * c[:, None]
    spec[-(n // 2 - 1):] = np.conj((hk * c[:, None])[::-1])
    t = (np.fft.ifft(spec, axis=0).real * n + tab.average() * rs.h0[None, :]).max(axis=1)
    return float(t.max() - t.min())


def part_tables():
    """!
    @brief Power tables on the 10 mm part of the two-layer board against the reference.
    """
    rect = centred(10)
    col, _ = S.column_for_heater(full_board(2, rect), 0)
    rs = R.Response(R.Reference(R.Board(layers=2), R.Case(part=tuple(v * MM for v in rect)), quarter=True))
    tabs = {"20 Hz, 3 levels 10/5/0 W (10, 10, 30 ms)": TableProfile([0, .01, .02, .05], [10., 5., 0.]),
            "1 Hz, 4 levels 8/2/6/0 W (0.1, 0.3, 0.1, 0.5 s)": TableProfile([0, .1, .4, .5, 1.], [8., 2., 6., 0.]),
            "100 Hz, two 1 ms pulses of 10 W in 10 ms": TableProfile([0, 1e-3, 3e-3, 4e-3, 1e-2], [10., 0., 10., 0.]),
            "0.2 Hz, 1 s at 10 W, 4 s at 2 W": TableProfile([0, 1., 5.], [10., 2.])}
    for lab, tb in tabs.items():
        r = col.profile_ripple(tb)
        b = _ref_profile_swing(rs, tb)
        print(f"table {lab}: closed form {r.plus - r.minus:.4f} K, reference {b:.4f} K, ratio {(r.plus - r.minus) / b:.3f}", flush=True)


def part_vias():
    """!
    @brief Vias under the 10 mm part, by density, two and four layers: closed form / reference at duty 30 %.
    """
    for lab, grid in (("4 vias, 2 x 2, pitch 5 mm", [-2.5, 2.5]), ("9 vias, 3 x 3, pitch 3.33 mm", [-10 / 3, 0, 10 / 3]),
                      ("16 vias, 4 x 4, pitch 2.5 mm", [-3.75, -1.25, 1.25, 3.75]), ("36 vias, 6 x 6, pitch 1.5 mm", [-3.75, -2.25, -0.75, 0.75, 2.25, 3.75])):
        vs = [(30 + x, 20 + y) for x in grid for y in grid]
        for L in (2, 4):
            p = full_board(L, centred(10), vias=vs)
            rs = R.Response(R.Reference(R.Board(layers=L), R.Case(part=tuple(v * MM for v in centred(10)), vias=[(x * MM, y * MM) for x, y in vs]), quarter=True))
            row = [closed(p, f, 0.3) / rs.swing(1.0 / f, 0.3) for f in (0.1, 1, 10, 100, 1000)]
            print(f"vias {lab}, {L} layers: " + " ".join(f"{x:.3f}" for x in row), flush=True)


def part_partial():
    """!
    @brief Copper on the left half of the 10 mm part only (fill 0.5: the closed form does not apply): the program's decision against the reference.
    """
    rect = centred(10)
    p = Problem.new(W, H, 2, 1.6, h_top=10, h_bottom=10, h_side=0.0)
    p.add_zone(1, rect=(0, 0, 30, 40))
    p.add_zone(2, rect=(0, 0, W, H))
    p.add_heater(1, 1.0, rect=rect, name="u", profile=SquareWave(p_on=1.0, period=1.0, duty=0.3))
    print("status", S.column_for_heater(p, 0)[1])
    resp = profiles.step_response_fvm(p, 1.0)
    rs = R.Response(R.Reference(R.Board(layers=2), R.Case(part=tuple(v * MM for v in rect), no_copper=[(0, (30 * MM, 0, W * MM, H * MM))]), quarter=False, top_first=0.05e-6))
    for f in (0.1, 1, 3, 10, 100, 1000):
        p.heaters[0].set_profile(SquareWave(p_on=1.0, period=1 / f, duty=0.3))
        d = profiles.decide(p, resp, 1e9)[0]
        b = rs.swing(1 / f, 0.3)
        print(f"partial copper {f} Hz: program {d.oscillation:.4f} reference {b:.4f} ratio {d.oscillation / b:.3f}", flush=True)


def part_conv():
    """!
    @brief Convergence of the reference at 3 and 10 kHz (1 layer, 2 mm): the default grid against copper in 12 cells and a 0.2 um first laminate cell.
    """
    rect = centred(2)
    p = full_board(1, rect)
    for n_cu, first in ((6, 0.5e-6), (12, 0.2e-6)):
        rs = R.Response(R.Reference(R.Board(layers=1), R.Case(part=tuple(v * MM for v in rect)), quarter=True, n_cu=n_cu, first=first), f_hi=3e6)
        print(f"reference with {n_cu} copper cells, first cell {first * 1e6:g} um: " + " ".join(
            f"{f:g} Hz D {d:g} {closed(p, f, d) / rs.swing(1 / f, d):.3f}" for f in (3000, 10000) for d in (0.1, 0.5)), flush=True)


def part_models():
    """!
    @brief The Lumped and Analytic step responses against the closed form, and a profile run of every model with a fast wave.
    """
    p = full_board(2, centred(10), profile=SquareWave(p_on=1.0, period=1.0, duty=0.5))
    o = api.SolverOptions(models=("fvm",), cell_mm=1.0)
    resp = {m: api.step_response(p, m, o) for m in ("fvm", "lumped", "analytic")}
    for f in (0.1, 1, 10, 100):
        w = SquareWave(p_on=1.0, period=1 / f, duty=0.5)
        p.heaters[0].set_profile(w)
        cf = closed(p, f, 0.5)
        print(f"{f:g} Hz node / closed form: " + " ".join(f"{m} {(lambda a: (a[0] - a[1]) / cf)(profiles.wave_response(r, 0, w)):.3f}" for m, r in resp.items()))
    for m in ("fvm", "fdm", "lumped", "analytic"):
        q = full_board(2, centred(10), profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
        sim = api.simulate(q, api.SolverOptions(models=(m,), cell_mm=2.0))
        r = sim.profile_results[m]
        print(f"run {m}: {sim.decisions[0].regime}, ripple {r.ripple[0]['swing_c']:.3f} K, peak {r.peak:.3f}, minimum {r.minimum:.3f}, steps {r.steps}")


def part_cross():
    """!
    @brief The closed-form wave of a neighbour (two 10 mm parts on an infinite sheet, in phase): cross swing / own swing, by gap and frequency, duty 50 %.
    """
    col, _ = S.column_for_heater(full_board(2, centred(10)), 0)
    a = col.radius
    side = np.sqrt(np.pi) * a

    def cross(r, period, n=16384):
        """!
        @brief Peak-to-peak of the neighbour's wave at distance r (closed form of an infinite sheet: m a I1(m a) K0(m r) / (pi a^2 Y)).
        @param r Centre-to-centre distance in m.
        @param period Period in s.
        @param n Samples per period.
        @return K per W of swing.
        """
        k = np.arange(1, n // 2)
        y = col.admittance(k * 2 * np.pi / period)
        m = np.sqrt(y / col.sheet)
        z = m * a * iv(1, m * a) * kv(0, m * r) / (np.pi * a * a * y)
        c = (1 - np.exp(-2j * np.pi * k * 0.5)) / (2j * np.pi * k) * np.sinc(k / (n // 2))
        spec = np.zeros(n, complex)
        spec[1:n // 2] = z * c
        spec[-(n // 2 - 1):] = np.conj((z * c)[::-1])
        t = np.fft.ifft(spec).real * n
        return t.max() - t.min()

    for f in (0.1, 1, 10, 100):
        s = col.swing(1 / f, 0.5)
        print(f"{f:g} Hz: " + " ".join(f"gap {g:g} mm {cross(side + g * MM, 1 / f) / s:.3f}" for g in (1, 2, 5, 10)))


def part_cell():
    """!
    @brief Cost of the finer step response of api.response_cell_mm on a 100 x 80 mm board with a 10 mm part and a small one with a profile.
    """
    import resource
    for L in (2, 4):
        for side in (2.0, 5.0):
            p = Problem.new(100, 80, L, 1.6, h_top=10, h_bottom=10, h_side=0.0).add_full_copper()
            p.add_heater(1, 1.0, rect=(50 - side / 2, 40 - side / 2, 50 + side / 2, 40 + side / 2), name="u", profile=SquareWave(p_on=1.0, period=10.0, duty=0.3))
            p.add_heater(1, 2.0, rect=(20, 20, 30, 30), name="v")
            o = api.SolverOptions(models=("fvm",), cell_mm=1.0)
            t = time.time()
            r = api.step_response(p, "fvm", o)
            t1 = time.time() - t
            t = time.time()
            r2 = profiles.step_response_fvm(p, 2.0)
            t2 = time.time() - t
            d = profiles.decide(p, r, 1e9)[0]
            n1, n2 = profiles.wave_response(r, 0, p.heaters[0].profile), profiles.wave_response(r2, 0, p.heaters[0].profile)
            print(f"{L} layers, {side:g} mm part: cell {api.response_cell_mm(p, 'fvm', o):.2f} mm, {t1:.1f} s (2 mm: {t2:.1f} s); node / closed form "
                  f"{(n1[0] - n1[1]) / d.ripple_swing:.2f} (2 mm: {(n2[0] - n2[1]) / d.ripple_swing:.2f}); peak memory so far {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9:.2f} GB", flush=True)


def part_envelope():
    """!
    @brief The extremes about the mean that the ripple run adds (plus, minus) against the hottest-cell wave of the reference minus its mean (10 mm part, 2 layers).
    """
    rect = centred(10)
    col, _ = S.column_for_heater(full_board(2, rect), 0)
    rs = R.Response(R.Reference(R.Board(layers=2), R.Case(part=tuple(v * MM for v in rect)), quarter=True))
    for f, d in ((20, 0.3), (5, 0.3), (1, 0.1), (0.2, 0.1), (100, 0.5)):
        w = rs.wave(1 / f, d).max(axis=1)
        mean = d * rs.h0.max()
        r = col.ripple(1 / f, d)
        print(f"{f:g} Hz duty {d:g}: plus {r.plus / (w.max() - mean):.3f}, minus {r.minus / (w.min() - mean):.3f}", flush=True)


PARTS = {"envelope": part_envelope, "saved": part_saved, "table371": part_table371, "fresh": part_fresh, "tables": part_tables, "vias": part_vias, "partial": part_partial, "conv": part_conv,
         "models": part_models, "cross": part_cross, "cell": part_cell}

if __name__ == "__main__":
    for name in sys.argv[1:] or ["saved", "table371", "models", "cross"]:
        print(f"== {name}", flush=True)
        PARTS[name]()
