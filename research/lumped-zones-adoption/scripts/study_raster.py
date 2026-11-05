#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_raster.py
@brief Study 3: the Lumped raster cell (0.5, 0.75, 1.0 mm and the cell tied to the core) against the accuracy of the zone model and of the program.
@details The program runs the Lumped model at a cell clipped to 0.5 to 1.0 mm, 1.0 mm by default for any part wider than 4 mm. The zone model needs a core of several cells; the earlier folder found the
         zone model at 8.0 % mean / 20.8 % maximum at 1.0 mm against 3.6 / 9.1 % at 0.5 mm (misses on the safe side, cores three to seven cells across). This study repeats that sweep on the 2.4.5
         program with the 36 boards of the family and the 26 held-out boards, in the variants `P245` and the zone variant chosen by study 1 (`--variant`, default `Z_none`), at the fixed cells
         0.5, 0.75 and 1.0 mm and at the cell tied to the core by `zoned_lumped.tied_cell_mm` (a tenth of the narrowest core, between 0.5 and 1.0 mm). It also prints how many boards get each
         warning of `zoned_lumped.zone_warnings` ("core under ten cells across") at each cell, and the time of one run, so that the cost of the finer cell is a number.
         Success criterion (fixed before running): the tied cell brings the zone variant within 6 % mean on the 36 boards and removes the warning "coarser than a tenth of the core" on every board
         whose core is at least 5 mm across; the extra run time on the example board stays under 2 times that of 1.0 mm.
Usage: python research/lumped-zones-adoption/scripts/study_raster.py [--variant Z_none|Z_cap] [--quick] [--procs N]   (from the repository root; uses the references of study 1)
"""

import argparse
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402

CELLS = (0.5, 0.75, 1.0, "tied")
VARIANT = {"v": "Z_none"}


def one(item):
    """!
    @brief The via effect of the program and of the chosen zone variant at every cell for one board.
    @param item (label, spec, variant).
    @return dict with label, E_ref, err {variant: {cell: percent}}, warnings {cell: [text]}.
    """
    label, spec, variant = item
    e_ref = zref.refs.reference(spec)["E"]
    prob = zref.refs.make_problem(spec)
    out, warn = {"P245": {}, variant: {}}, {}
    for cell in CELLS:
        c = zl.tied_cell_mm(prob, 1.0) if cell == "tied" else cell
        for name in ("P245", variant):
            out[name][str(cell)] = zref.error_pct(zref.lumped_E(spec, name, c), e_ref)
        with zref.VARIANTS[variant]():
            zref.pc.max_rise(prob, "lumped", c)                              # builds the network: the diagnostics of the last heater are in zl.LAST
            warn[str(cell)] = list(zl.LAST.get("warnings", []))
    return {"label": label, "E_ref": e_ref, "err": out, "warnings": warn}


def main():
    """!
    @brief Run the sweep and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--variant", default="Z_none")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    args = ap.parse_args()
    import study_family
    import study_holdout
    items = [(f"family {i}", s, args.variant) for i, s in enumerate(study_family.specs(args.quick))]
    hold = [(lab, s, args.variant) for lab, s in study_holdout.holdout_specs()]
    with mp.get_context("spawn").Pool(args.procs) as pool:
        fam_rows = pool.map(one, items, chunksize=1)
        hold_rows = pool.map(one, hold[:4] if args.quick else hold, chunksize=1)
    for title, rows in (("Family", fam_rows), ("Held-out", hold_rows)):
        print(f"\n{title} ({len(rows)} boards): mean / max absolute error of E in percent, within 10 %\n")
        print("| variant | " + " | ".join(f"{c} mm" if c != "tied" else "tied" for c in CELLS) + " |\n| :-- |" + " --: |" * len(CELLS))
        for name in ("P245", args.variant):
            cells = []
            for c in CELLS:
                s = zref.summarize([r["err"][name][str(c)] for r in rows])
                cells.append(f"{s['mean']:.1f} / {s['max']:.1f}, {s['within']} of {s['n']}")
            print(f"| {name} | " + " | ".join(cells) + " |")
        print("\nboards with a warning (any / 'coarser than a tenth of the core' / 'elongated or off centre') per cell\n")
        for c in CELLS:
            w = [r["warnings"][str(c)] for r in rows]
            print(f"* {c}: {sum(bool(x) for x in w)} / {sum(any('coarser' in t for t in x) for x in w)} / {sum(any('elongated' in t for t in x) for x in w)}")
    # cost of the finer cell on the example board
    import study_real_boards as srb
    zref.pc.load_libraries()
    prob = srb.example(385.0, 0, 3.5)
    print("\nrun time of one Lumped solve of the example board (s), program / zones\n")
    for c in (1.0, 0.75, 0.5):
        times = []
        for name in ("P245", args.variant):
            with zref.VARIANTS[name]():
                t0 = time.perf_counter()
                zref.pc.max_rise(prob, "lumped", c)
                times.append(time.perf_counter() - t0)
        print(f"* {c} mm: {times[0]:.2f} / {times[1]:.2f}")
    print("\nwritten", zref.save_json("raster.json", {"family": fam_rows, "holdout": hold_rows}))


if __name__ == "__main__":
    main()
