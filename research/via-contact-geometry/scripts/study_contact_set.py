#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_contact_set.py
@brief The contact geometry of a via on a plane with copper over part of its footprint: the program and three candidate couplings against the 3D solid on fifteen boards.
@details The fifteen 10 x 10 mm boards of scripts/study_reference_set.py (copied from the review of the star coupling: full copper, arrays, a via at the corner of a copper quadrant,
         a track ending on the via, a via on bare laminate just outside a copper edge, a via near an edge or a corner). For every board and cell the via effect (maximum rise without
         the via minus with it) of the FVM and FDM with the program as it is (`current`), the sheet-weighted mean-potential via (`sheet`), the program's weights with the contact
         share on the well (`contact_geo`), and the sheet weights with the contact share (`contact`), against the 3D solid at 0.1 mm and 8 slabs (out/solid_8.json, written by
         `study_reference_set.py solid`). The barrel rule of lib/barrel.py can be added with `--barrel A`.
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_contact_set.py run [--barrel 0.5]` then `... table`.
"""

import argparse
import contextlib
import json
import sys

import _bootstrap  # noqa: F401

import barrel as BA
import contact as CT
import study_reference_set as RS

VARIANTS = ("current", "sheet", "contact_geo", "contact")
CELLS = (2.0, 1.0, 0.5, 0.25, 0.125)
OUTFILE = _bootstrap.OUT / "contact.json"


def main():
    """!
    @brief Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "table"))
    ap.add_argument("--barrel", type=float, default=0.0, help="extra barrel length per gap in units of the copper thickness (0 = the program)")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = _bootstrap.OUT / f"contact{a.tag}.json"
    if a.mode == "run":
        Problem, fvm, fdm, solid3d, load_project = RS.setup(str(_bootstrap.REPO))
        cases = RS.make_cases(Problem)
        res = {}
        for name, f in cases.items():
            res[f"rise|{name}"] = RS.layered_max(f(False), fvm, fdm, "fvm", 0.25)         # rise without the via (scale for the absolute errors)
        for variant in VARIANTS:
            with BA.patched(a.barrel), CT.patched(variant):
                for name, f in cases.items():
                    for kind in ("fvm", "fdm"):
                        for cell in CELLS:
                            e = RS.layered_max(f(False), fvm, fdm, kind, cell) - RS.layered_max(f(True), fvm, fdm, kind, cell)
                            res[f"{variant}|{name}|{kind}|{cell}"] = e
                print(variant, "done", flush=True)
        json.dump(res, open(out, "w"), indent=1)
        return
    solid = json.load(open(_bootstrap.OUT / "solid_8.json"))
    res = json.load(open(out))
    names = [k.split("|")[1] for k in res if k.startswith("rise|")]
    for kind in ("fvm", "fdm"):
        print(f"== {kind}: signed error of the via effect against the 3D solid (0.1 mm, 8 slabs), per cent; variants: " + ", ".join(VARIANTS))
        for n in names:
            ref = solid[f"{n}|solid|0.1|8"]
            row = f"{n:12s} 3D {ref:6.3f} K"
            for c in ("1.0", "0.5", "0.25"):
                row += f" | {c}: " + " ".join(f"{100 * (res[f'{v}|{n}|{kind}|{float(c)}'] / ref - 1):+5.0f}" for v in VARIANTS)
            print(row)
    print("== FVM: error of the via effect in K (and in per cent of the rise without the via); positive: the via is too effective, the part reads too cool (unsafe)")
    for n in names:
        ref = solid[f"{n}|solid|0.1|8"]
        row = f"{n:12s} rise {res[f'rise|{n}']:6.1f} K"
        for c in ("1.0", "0.5", "0.25"):
            row += f" | {c}: " + " ".join(f"{res[f'{v}|{n}|fvm|{float(c)}'] - ref:+5.2f}({100 * (res[f'{v}|{n}|fvm|{float(c)}'] - ref) / res[f'rise|{n}']:+4.1f})" for v in VARIANTS)
        print(row)


if __name__ == "__main__":
    sys.exit(main())
