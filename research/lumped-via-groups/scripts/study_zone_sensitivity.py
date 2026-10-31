#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_zone_sensitivity.py
@brief How the two-zone Lumped model depends on what it assumes: the layout of the vias in the footprint (off centre, a rectangular source, two clusters), the knobs of the model, the raster cell.
@details Base board: 4 layers of full copper, a 10 mm source on a 30 mm board, a 5 x 5 array of 0.3 mm vias at 1.2 mm (copper fill and open barrel). Part 1 changes the layout (the source and its array
         together off the centre of the board by 2 and 3 mm (the array stays centred in its footprint), a 17.6 x 6.9 mm source (side ratio 2.56; `src_aspect` 1.6 scales the sides by 1.6), two 3 x 3 clusters under a 14 mm source), part 2 the knobs of `lib/lumped_zones.py` (radius of the core around the vias in nearest-neighbour
         distances, the factor on the A-C link, the lossy link, the peak term off, the largest core share), part 3 the raster cell of the Lumped model (0.5, 0.75, 1 mm: the program clips it to 0.5 to 1 mm). The error of the via
         effect E against the fine-grid layered reference (`lib/refs.py`, cached) is printed in percent. The group-term variants `L_prog`, `L_nn`, `L_grp0` are given for scale.
Usage: python research/lumped-via-groups/scripts/study_zone_sensitivity.py   (from the repository root; the references take about 10 minutes the first time)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-analytic-vias", "lib"))

import harness as hz                                                         # noqa: E402
import lumped_zones as lz                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402
import refs                                                                  # noqa: E402

BASE = dict(layers=4, n=5, pitch=1.2, src=10.0)


def err(spec, factory, cell=0.5):
    """!
    @brief Error of E of one variant on one spec.
    @param spec Board spec.
    @param factory Context-manager factory.
    @param cell Raster cell of the Lumped model in mm.
    @return float percent.
    """
    ref = refs.reference(spec)
    p = refs.make_problem(spec)
    e = hz.effect(p, "lumped", factory, cell, hz.no_vias(p))
    return 100.0 * (e / ref["E"] - 1.0)


def main():
    """!
    @brief Run the three parts and print the tables.
    @return None.
    """
    pc.load_libraries()
    fills = (385.0, 0.0)
    print("## 1. Layout of the vias and of the source (error of E, percent)\n")
    layouts = [("5 x 5 at 1.2, centred", dict(BASE)), ("source and array 2 mm off the board centre", dict(BASE, offset=(2.0, 0.0))), ("source and array (3, 2) mm off the board centre", dict(BASE, offset=(3.0, 2.0))),
               ("source 17.6 x 6.9 mm (side ratio 2.56, 4.8 mm array)", dict(BASE, src=11.0, src_aspect=1.6)),
               ("two 3 x 3 clusters at 1.0 mm, 6 mm apart, source 14", dict(BASE, src=14.0, clusters=[(-3.0, 0.0, 3, 1.0), (3.0, 0.0, 3, 1.0)])),
               ("one 3 x 3 cluster off the centre of a 14 mm source", dict(BASE, src=14.0, clusters=[(2.5, 0.0, 3, 1.0)]))]
    names = {k: refs.VARIANTS[k] for k in ("L_prog", "L_nn", "L_grp0", "L_zone_disc", "L_zone_r", "L_zone")}
    print("| layout | fill | " + " | ".join(names) + " |\n| :-- | :-- |" + " --: |" * len(names))
    for label, spec in layouts:
        for fill in fills:
            sp = dict(spec, fill=fill)
            print(f"| {label} | {'Cu' if fill else 'open'} | " + " | ".join(f"{err(sp, f):+.1f}" for f in names.values()) + " |", flush=True)
    print("\n## 2. Knobs of the zone model (5 x 5 at 1.2 mm under 10 mm, error of E, percent)\n")
    knobs = [("as proposed (real shapes, lossy peak, micro peak, bump of a hot core)", {}), ("the researcher's proposal (L_zone_r: no bump of a hot core, strided decimation)", dict(refs.OLD)),
             ("concentric discs, closed forms (L_zone_disc)", dict(geometry="disc", core_int=1.0, peak="annulus", **refs.OLD)), ("lossless peak of the real shapes", dict(peak="potential")), ("annulus peak", dict(peak="annulus")),
             ("no micro peak", dict(micro_peak=False)), ("core radius 0.5 d_nn", dict(core_r=0.5)), ("core radius 1.0 d_nn", dict(core_r=1.0)),
             ("link x 0.75", dict(link_scale=0.75)), ("link x 1.25", dict(link_scale=1.25)), 
             ("through-flow link to ring 1 in the layers without the source", dict(a1_other="through")), ("no peak term of the zones", dict(peak="none")), ("max core 0.5 (no split above)", dict(max_core=0.5)), ("no micro well (effective vertical conductivity)", dict(micro_scale=0.0))]
    print("| knob | Cu | open |\n| :-- | --: | --: |")
    for label, kw in knobs:
        vals = [err(dict(BASE, fill=f), (lambda kw=kw: lz.patched(**kw))) for f in fills]
        print(f"| {label} | {vals[0]:+.1f} | {vals[1]:+.1f} |", flush=True)
    print("\n## 3. Raster cell of the Lumped model (5 x 5 at 1.2 mm under 10 mm, error of E, percent)\n")
    # the program clips the cell of the Lumped model to 0.5 to 1.0 mm (api: min(max(cell_mm, 0.5), 1.0)), so a 0.25 mm row would be the 0.5 mm run again (the review found
    # that the earlier table had such a row); the program's default and Auto cell give 1.0 mm for any part wider than 4 mm
    print("| cell mm | L_prog Cu | L_zone_disc Cu | L_zone_r Cu | L_zone Cu | L_prog open | L_zone_disc open | L_zone_r open | L_zone open |\n| --: |" + " --: |" * 8)
    for cell in (0.5, 0.75, 1.0):
        v = [err(dict(BASE, fill=f), refs.VARIANTS[k], cell) for f in fills for k in ("L_prog", "L_zone_disc", "L_zone_r", "L_zone")]
        print(f"| {cell} | " + " | ".join(f"{x:+.1f}" for x in v) + " |", flush=True)


if __name__ == "__main__":
    main()
