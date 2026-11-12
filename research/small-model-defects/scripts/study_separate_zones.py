#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_separate_zones.py
@brief Item 2: a 4-layer board with separate copper zones: is the Lumped model mirror-symmetric, and why is the FDM below the FVM?
@details Builds a family of boards (separate top-layer zones, each with a part, inner planes or none), runs FVM, FDM, Lumped and Analytic on the board and on its mirror
         image (x -> W - x), at 1 and 0.5 mm, and prints the hottest temperature of each and the mirror difference. The controlled experiments of the README (which
         ingredient makes the difference) are the options of `make`: zone_gap, inner planes, bottom copper, part off the zone centre, h_side.
         Usage: python research/small-model-defects/scripts/study_separate_zones.py [--quick]   (from the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from pcbthermal.api import SolverOptions, simulate                          # noqa: E402
from pcbthermal.model import Problem                                        # noqa: E402

MODELS = ("fvm", "fdm", "lumped", "analytic")


def make(mirror=False, gap=6.0, inner="planes", bottom=True, h_side=10.0, offset=0.0, W=80.0, H=50.0, layers=4, parts=2, zone_w=30.0):
    """!
    @brief Board with separate top zones, one part on each (or one), inner planes optional.
    @param mirror True for the image of the board in x -> W - x.
    @param gap Gap between the two top zones in mm.
    @param inner "planes" (full inner layers), "none" (no inner copper) or "one" (only layer 2).
    @param bottom True for a full bottom plane.
    @param h_side Edge coefficient in W/m2K.
    @param offset Shift in mm of the part inside its zone towards the zone's outer end (breaks the symmetry of the part against its zone).
    @param W Board width in mm.
    @param H Board height in mm.
    @param layers Layers (4).
    @param parts 2 (a 2 W part on the left zone and a 1 W part on the right one) or 1 (left zone only).
    @param zone_w Width of each top zone in mm.
    @return Problem.
    """
    p = Problem.new(W, H, layers=layers, h_top=10.0, h_bottom=15.0, h_side=h_side)
    xa0 = W / 2 - gap / 2 - zone_w
    xb0 = W / 2 + gap / 2
    zones = [(xa0, 5, xa0 + zone_w, H - 5), (xb0, 5, xb0 + zone_w, H - 5)]
    parts_list = [(xa0 + zone_w / 2 + offset, H / 2, 2.0), (xb0 + zone_w / 2 - offset, H / 2, 1.0)][:parts]

    def fx(x0, x1):
        """!
        @brief Mirror an x interval.
        @param x0 Left end.
        @param x1 Right end.
        @return (x0', x1').
        """
        return (W - x1, W - x0) if mirror else (x0, x1)
    for (a, b, c, d) in zones:
        x0, x1 = fx(a, c)
        p.add_zone(1, rect=(x0, b, x1, d))
    for cx, cy, pw in parts_list:
        x0, x1 = fx(cx - 3, cx + 3)
        p.add_heater(1, pw, rect=(x0, cy - 3, x1, cy + 3))
    if inner == "planes":
        p.add_full_copper([2, 3])
    elif inner == "one":
        p.add_full_copper([2])
    if bottom:
        p.add_full_copper([layers])
    return p


def run(p, cell, models=MODELS):
    """!
    @brief Hottest temperatures.
    @param p Problem.
    @param cell Cell in mm.
    @param models Model keys.
    @return dict.
    """
    s = simulate(p, SolverOptions(models=models, cell_mm=cell))
    return {k: float(r.t_max) for k, r in s.results.items()}


def table(title, kwargs_list, cells=(1.0, 0.5)):
    """!
    @brief Print one table: for each variant the four models, the FDM/FVM ratio of the rise, and the mirror difference of every model.
    @param title Table title.
    @param kwargs_list List of (label, kwargs of make).
    @param cells Cells in mm.
    @return None.
    """
    print(f"\n== {title} ==")
    print("variant | cell | FVM | FDM | Lumped | Analytic (rise over 25 degC ambient) | FDM/FVM rise | mirror diff FVM / FDM / Lumped / Analytic (K)")
    for label, kw in kwargs_list:
        for cell in cells:
            a = run(make(False, **kw), cell)
            b = run(make(True, **kw), cell)
            rise = {k: v - 25.0 for k, v in a.items()}
            md = " / ".join(f"{b[k] - a[k]:+.3f}" for k in MODELS)
            print(f"{label} | {cell} | " + " | ".join(f"{rise[k]:.2f}" for k in MODELS) + f" | {rise['fdm'] / rise['fvm']:.3f} | {md}", flush=True)


def main():
    """!
    @brief Run the tables.
    @return None.
    """
    quick = "--quick" in sys.argv
    table("1. The family: separate zones (gap 6 mm), inner planes and bottom plane", [("base", {})], cells=(1.0,) if quick else (1.0, 0.5))
    if quick:
        return
    table("2. Zone gap", [(f"gap {g}", {"gap": g}) for g in (0.0, 2.0, 6.0, 20.0)])
    table("3. Inner copper", [("planes", {}), ("one plane", {"inner": "one"}), ("none", {"inner": "none"}), ("none, no bottom", {"inner": "none", "bottom": False})], cells=(1.0,))
    table("4. Edge coefficient", [("h_side 0", {"h_side": 0.0}), ("10", {}), ("50", {"h_side": 50.0})], cells=(1.0,))
    table("5. One part only", [("1 part", {"parts": 1})], cells=(1.0,))
    table("6. Part offset in the zone", [("offset 0", {}), ("offset 4 mm", {"offset": 4.0})], cells=(1.0,))


if __name__ == "__main__":
    main()
