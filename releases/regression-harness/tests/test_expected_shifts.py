#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_expected_shifts.py
@brief Test of `make_expected_shifts.attribute`: a record is credited to the pending file that holds it and to every item named in `also_moved_by`.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parent / "scripts"))

import make_expected_shifts as M                                            # noqa: E402


def test_also_moved_by_credits_every_item():
    """!
    @brief The film file holds a record that an older file moved too: both items are credited, for a record and for a time.
    @return None
    """
    P = {"face-film": {"records": {"b|fvm|2": {}}, "transients": {"b|fvm": {}},
                       "also_moved_by": {"b|fvm|2": ["drawn"], "t63:b|fvm": ["first-link"]}},
         "other": {"records": {"c|fvm|2": {}}}}
    ID = {"face-film": "F"}
    assert M.attribute("b|fvm|2", P, ID) == ("F", "drawn")
    assert M.attribute("b|fvm", P, ID, "transients", "t63:") == ("F", "first-link")
    assert M.attribute("c|fvm|2", P, ID) == ("other",)
    assert M.attribute("z|fvm|2", P, ID) == ()
