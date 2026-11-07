#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen.py
@brief Which frozen-regression records would move under the barrel rule and the contact coupling, and by how much (FVM and FDM, steady maximum, 2, 1 and 0.5 mm).
@details For every board of tests/regression/regress_boards.py that has vias: the maximum temperature with the program as it is, with the barrel rule a = 0.5 (lib/barrel.py),
         with the contact coupling (lib/contact.py, `contact`) and with both. Boards whose vias all sit on uniform full copper must show exactly 0.0000 K under the contact
         coupling (it hands such vias to the program's code). Also prints the shift of the time to 63 % of the FVM step response is NOT computed here (steady maximum only).
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_frozen.py`; writes out/frozen.json.
"""

import json
import logging
import sys

import _bootstrap  # noqa: F401

import barrel as BA
import contact as CT
import regress_boards as B

from pcbthermal import fdm, fvm

logging.disable(logging.WARNING)


def tmax(problem, model, cell):
    """!
    @brief Maximum temperature of a layered steady run.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return float in degC.
    """
    return float((fvm.solve_steady if model == "fvm" else fdm.solve_steady)(problem, cell).t_max)


def main():
    """!
    @brief Run and print.
    @return None.
    """
    rows = {}
    print(f"{'board':22s} {'vias':>5s} {'cell':>5s} {'model':5s} {'base degC':>10s} {'rise':>7s} {'d barrel':>9s} {'d contact':>9s} {'d both':>9s}  (K; barrel a = 0.5)")
    for name in B.board_names():
        p = B.build(name)
        if not p.vias:
            continue
        for cell in (2.0, 1.0, 0.5):
            for model in ("fvm", "fdm"):
                base = tmax(B.build(name), model, cell)
                amb = B.build(name).board.ambient
                with BA.patched(0.5):
                    d_b = tmax(B.build(name), model, cell) - base
                with CT.patched("contact"):
                    d_c = tmax(B.build(name), model, cell) - base
                with BA.patched(0.5), CT.patched("contact"):
                    d_bc = tmax(B.build(name), model, cell) - base
                rows[f"{name}|{cell}|{model}"] = dict(vias=len(p.vias), base=base, rise=base - amb, barrel=d_b, contact=d_c, both=d_bc)
                print(f"{name:22s} {len(p.vias):5d} {cell:5.1f} {model:5s} {base:10.3f} {base - amb:7.2f} {d_b:+9.4f} {d_c:+9.4f} {d_bc:+9.4f}", flush=True)
    with open(_bootstrap.OUT / "frozen.json", "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    sys.exit(main())
