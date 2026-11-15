#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_expected_shifts_2_8_0.py
@brief Tests of the preview table of 2.8.0: every shift that the pending files hold is covered by a rule of the table, the additions are not shifts, nothing reaches the 3D solid.
@details Light: it reads the committed frozen file and the pending files and runs no solver. Run from the repository root:

         .venv/bin/python -m pytest -q releases/2.8.0/refreeze/tests
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import make_expected_shifts_2_8_0 as T                                      # noqa: E402
import regress_classify as C                                                # noqa: E402


def _table():
    """!
    @brief The table built in memory from the frozen file and the pending files (the file on disk is not read).
    @return tuple (table, base, final, P).
    """
    base, final, tb, tf, P = T.load_preview()
    return T.build_table(base, final, tb, tf, P, preview=True), base, final, P


def test_every_shift_of_the_pending_files_is_expected_by_the_table():
    """!
    @brief Each moved metric of each frozen record, and each time to 63 %, is classified `expected` against the table made from the same numbers: no `??`, no alarm.
    @return None
    """
    table, base, final, P = _table()
    assert not [r for r in table["rules"] if "??" in r["item"]]
    n = 0
    for k, mf in final.items():
        bd, m, c = k.split("|")
        mb = base[k]
        rise = mb["t_max"] - 20.0                                          # only the size of the rise matters to the `rel_rise` bounds of the derived rules
        for name in mf:
            if name in mb and mf[name] != mb[name]:
                cls, rules, _ = C.classify_shift(table, bd, m, float(c), name, mb[name], mf[name], rise)
                assert cls == "expected", (k, name, cls)
                n += 1
    assert n > 1000                                                        # the pending files move about 1400 numbers of 17 boards


def test_additions_are_not_shifts_and_the_3d_solid_is_held():
    """!
    @brief The surface read-out is an added metric of the FVM, FDM and SOR runs (not of the Lumped), the finite-element records are not in the baseline, the 3D solid is must-not-move.
    @return None
    """
    table, base, final, P = _table()
    scope = lambda model, name: [r for r in table["added_metrics"] if C.scope_matches(r, "example_board", model, 1.0, name)]
    assert scope("fvm", "surface:top:t_max") and scope("fdm", "part:U1:t_max_surface") and scope("fvm_sor", "surface:bottom:t_mean")
    assert not scope("lumped", "surface:top:t_max") and not scope("fvm", "t_max")
    assert not [k for k in base if "|fem|" in k]                         # the finite-element records exist only in the new set
    assert all(P[n].get("new_models") for n in ("fem-records",)) and P["surface-records"].get("new_readouts")
    assert C.classify_shift(table, "plate_uniform", "solid3d", 1.0, "t_max", 50.0, 50.001, 30.0)[0] == "must_not_move"


def test_a_file_of_additions_is_never_the_item_of_a_shift():
    """!
    @brief `fem-records` and `surface-records` hold the same keys as the shifts but credit no item to them; a `drawn_*` board gets its items by model.
    @return None
    """
    base, final, tb, tf, P = T.load_preview()
    assert T.items_of("example_board|fvm|1", "fvm", P) == ("M1",)
    assert T.items_of("example_board|lumped|1", "lumped", P) == ("M1", "M3")
    assert T.items_of("finned_block|analytic|1", "analytic", P) == ("M1", "M4")
    assert T.items_of("example_board|fvm|2", "fvm", P) == ("M1", "M2")
    assert T.items_of("drawn_ell|fdm|1", "fdm", P) == ("M1", "M2") and T.items_of("drawn_ell|analytic|1", "analytic", P) == ("M1",)
    assert T.items_of("plate_uniform|solid3d|1", "solid3d", P) == ()
