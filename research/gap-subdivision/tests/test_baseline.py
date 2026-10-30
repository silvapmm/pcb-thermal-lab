#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_baseline.py
@brief Tripwire on the committed baseline: the stored peaks of a few rows are reproduced by the program as it is, and the stored errors have the properties the README states.
@details When a change of the program moves these numbers on purpose, run `scripts/rerun_baseline.py --update` and read what moved; this test is meant to fail then, so that the baseline is not forgotten.
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import boards as B                                                           # noqa: E402
import rerun_baseline as RB                                                  # noqa: E402


def _rows(name):
    """!
    @brief Rows of a baseline CSV.
    @param name File name in baseline/.
    @return list of dict.
    """
    with open(os.path.join(HERE, "baseline", name)) as fh:
        return list(csv.DictReader(fh))


def test_uniform_rows_are_reproduced_and_small():
    """!
    @brief Three uniform rows re-run to 1e-4 relative; on every row of the sweeps the FVM, FDM, Analytic and 3D solid are within 2.5 % of the exact series except at a 2 mm cell.
    @return None.
    """
    rows = _rows("uniform.csv")
    for r in rows[:3]:
        res = B.all_models(RB.uniform_board(r), float(r["cell_mm"]), None, ("fvm", "analytic"))
        for m in ("fvm", "analytic"):
            assert abs(res[m][0] / float(r[f"{m}_K"]) - 1) < 1e-4
    for r in rows:
        if float(r["cell_mm"]) >= 2.0:
            continue
        for m in ("fvm", "fdm", "analytic", "solid3d"):
            assert abs(float(r[f"{m}_K"]) / float(r["ref_K"]) - 1) < 0.025


def test_pad_rows_are_reproduced_and_have_the_stated_shape():
    """!
    @brief Two pad rows re-run to 1e-4; the FVM shortfall grows as the pad gets smaller (bottom full) and with the gap (10 mm pad); energy balance of every reference is 1 to 1e-6.
    @return None.
    """
    rows = _rows("pads.csv")
    pick = [r for r in rows if r["tag"] in ("pad10-full", "L4-gap0.2-top-pad")]
    for r in pick:
        res = B.all_models(RB.pad_board(r), float(r["cell_mm"]), None, ("fvm",))
        assert abs(res["fvm"][0] / float(r["fvm_K"]) - 1) < 1e-4
    err = {r["tag"]: float(r["fvm_K"]) / float(r["ref_K"]) - 1 for r in rows}
    assert err["pad6-full"] < err["pad10-full"] < err["pad14-full"] < err["pad20-full"] < err["pad26-full"] <= 0.0
    assert err["gap3.2-full"] < err["gap1.6-full"] < err["gap0.4-full"]
    assert all(abs(float(r["ref_balance"]) - 1) < 1e-6 for r in rows)
