#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analyze.py
@brief Prints the tables of the README from the two caches written by run_ref.py and run_prog.py (out/ref_cache.jsonl, out/prog_cache.jsonl).
@details Question: which part of the error at a strongly cooled edge belongs to the plate (no via), to the via effect, and to the reference itself. Pure arithmetic on the caches.
         Run from the repository root: `.venv/bin/python research/strong-edge-laminate/scripts/analyze.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_prog as rp                                               # noqa: E402
import run_ref as rr                                                # noqa: E402

REF = rr.load()
PRG = rp.load()


def ref(h, n=8, dx=8, via="none", d=0.16, i=0.0):
    """!
    @brief Reference tmax or None.
    @param h Edge coefficient in W/m2K.
    @param n Sub-slabs per gap.
    @param dx Inverse plan cell in 1/mm.
    @param via Via representation.
    @param d Via distance in mm.
    @param i Copper inset in mm.
    @return float or None.
    """
    r = REF.get(rr.key(h, n, dx, via, 0.0 if via == "none" else d, i))
    return None if r is None else r["tmax"]


def prg(h, c, n=None, d=None, i=0.0):
    """!
    @brief Program rise or None.
    @param h Edge coefficient in W/m2K.
    @param c Cell in mm.
    @param n Sub-gaps (None: defaults).
    @param d Via distance in mm (None: no via).
    @param i Copper inset in mm.
    @return float or None.
    """
    r = PRG.get(rp.key(h, c, n, d, i))
    return None if r is None else r["rise"]


def f(x, nd=3):
    """!
    @brief Number to text, n/a for None.
    @param x Value or None.
    @param nd Decimals.
    @return str.
    """
    return "n/a" if x is None else f"{x:.{nd}f}"


def pct(a, b):
    """!
    @brief Percent difference of a against b.
    @param a Value.
    @param b Reference.
    @return str.
    """
    return "   n/a" if a is None or b is None else f"{100 * (a / b - 1):+6.1f}"


def eff(none, via):
    """!
    @brief Via effect none - via, or None.
    @param none Rise without the via.
    @param via Rise with it.
    @return float or None.
    """
    return None if none is None or via is None else none - via


def table_plate():
    """!
    @brief Section 3: the plate alone (no via).
    @return None.
    """
    print("\n== Plate alone: program rise without via against the 3D reference (dx 1/8, 8 sub-slabs), % ==")
    print("h_side  ref K   | cell 1 mm: n=2(def) 4 8 16 32 | cell 0.5 mm: n=2 4 8 16 32 | cell 0.25: n=2 4 8 16 32")
    for h in (10, 200, 500, 1000, 2000):
        r = ref(h)
        cols = []
        for c in (1.0, 0.5, 0.25):
            cols.append(" ".join(pct(prg(h, c, n), r) for n in (None, 4, 8, 16, 32)))
        print(f"{h:6g} {f(r, 3):>8} | " + " | ".join(cols))


def table_via():
    """!
    @brief Section 4: the via effect at 0.16 mm from the edge.
    @return None.
    """
    print("\n== Via effect E (0.16 mm from the wall): reference E (cyl / link) and program error % ==")
    print("h_side  E_cyl   E_link  | cell 1: n=2 4 8 16 32 | cell 0.5: n=2 4 8 16 32 | cell 0.25: n=2 4 8 16 32  (against E_cyl)")
    for h in (10, 200, 500, 1000, 2000):
        e = eff(ref(h), ref(h, via="cyl"))
        el = eff(ref(h), ref(h, via="link"))
        cols = []
        for c in (1.0, 0.5, 0.25):
            cols.append(" ".join(pct(eff(prg(h, c, n), prg(h, c, n, 0.16)), e) for n in (None, 4, 8, 16, 32)))
        print(f"{h:6g} {f(e, 4):>7} {f(el, 4):>7} | " + " | ".join(cols))


def table_ref_sens():
    """!
    @brief Section 5: sensitivity of the reference at h_side 1000.
    @return None.
    """
    print("\n== Reference sensitivity at h_side 1000: tmax none / cyl / link and E ==")
    for n, dx in ((2, 8), (4, 8), (8, 8), (16, 8), (32, 8), (8, 4), (8, 12), (4, 16), (8, 16)):
        a, b, c = ref(1000, n, dx), ref(1000, n, dx, "cyl"), ref(1000, n, dx, "link")
        e = eff(a, b)
        el = eff(a, c)
        print(f"n_sub {n:2d} dx 1/{dx:<2d}: none {f(a, 4)}  cyl {f(b, 4)}  E_cyl {f(e, 4)}  E_link {f(el, 4)}")


def table_dist():
    """!
    @brief Section 6: via distance and copper inset at h_side 200 and 1000 (cell 0.5 and 0.25 mm, dx 1/8 reference).
    @return None.
    """
    print("\n== Via distance: E reference (cyl) vs program (cells 0.5 / 0.25; n = default / 8 / 16), error % ==")
    for h in (200, 1000):
        for dist in (0.16, 0.5, 1.0, 3.0):
            e = eff(ref(h), ref(h, via="cyl", d=dist))
            row = []
            for c in (0.5, 0.25):
                for n in (None, 8, 16):
                    row.append(pct(eff(prg(h, c, n), prg(h, c, n, dist)), e))
            print(f"h {h:5g} dist {dist:4g}: E_ref {f(e, 4)}  | " + " ".join(row))
    print("\n== Copper inset 0.5 mm, via at 1.0 mm: plate error and E error % (cells 0.5 / 0.25; n = default / 8 / 16) ==")
    for h in (200, 1000):
        r0 = ref(h, i=0.5)
        e = eff(r0, ref(h, via="cyl", d=1.0, i=0.5))
        plate = [pct(prg(h, c, n, None, 0.5), r0) for c in (0.5, 0.25) for n in (None, 8, 16)]
        ee = [pct(eff(prg(h, c, n, None, 0.5), prg(h, c, n, 1.0, 0.5)), e) for c in (0.5, 0.25) for n in (None, 8, 16)]
        print(f"h {h:5g}: ref none {f(r0, 3)} E_ref {f(e, 4)} | plate " + " ".join(plate) + " | E " + " ".join(ee))


def table_fine():
    """!
    @brief The 0.125 mm program rows at h_side 1000.
    @return None.
    """
    print("\n== Program at the 0.125 mm cell, h_side 1000 ==")
    a0 = ref(1000)
    e = eff(a0, ref(1000, via="cyl"))
    for n in (None, 8, 16):
        a, b = prg(1000, 0.125, n), prg(1000, 0.125, n, 0.16)
        print(f"n={n}: plate {f(a, 3)} ({pct(a, a0)} %)  E {f(eff(a, b), 4)} ({pct(eff(a, b) if a is not None and b is not None else None, e)} %)")


if __name__ == "__main__":
    table_plate()
    table_via()
    table_ref_sens()
    table_dist()
    table_fine()
