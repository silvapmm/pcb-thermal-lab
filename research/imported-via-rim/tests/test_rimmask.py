#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_rimmask.py
@brief Tests of the mask rim prototype and of the 3D reference of the investigation `imported-via-rim`.
@details Run: .venv/bin/python -m pytest -q research/imported-via-rim/tests
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parent / "scripts"))
import rimmask                                                   # noqa: E402
import truth_via                                                 # noqa: E402
import study_synthetic as syn                                    # noqa: E402
from pcbthermal import viawell                                   # noqa: E402


def test_reference_balance_and_vias_help():
    """!
    @brief The reference closes the heat balance and a via field lowers the rise.
    @return None.
    """
    c = [(1.55e-3, 1.55e-3)]
    h = (0.9e-3, 0.9e-3, 2.2e-3, 2.2e-3)
    a = truth_via.solve(["solid", "solid"], c, h, width_mm=3.0, nlam=4)
    b = truth_via.solve(["solid", "solid"], c, h, width_mm=3.0, nlam=4, with_vias=False)
    assert abs(a["balance"]) < 1e-8
    assert a["max"] < b["max"]


def test_rim_shares_distinguish_antipad():
    """!
    @brief The drill circle gives 1.0 on a pad island inside an antipad (the program's rule); the ray test gives 0; a solid plane gives 1 and a relief a partial share.
    @return None.
    """
    centres = syn.via_centres(1)
    for kinds, expect in ((["solid", "solid"], (1.0, 1.0)), (["solid", "anti"], (1.0, 0.0)), (["solid", "relief"], (1.0, None))):
        p = syn.program_problem(kinds, centres)
        zi = viawell._zone_index(p, 2)
        v = p.vias[0]
        drill = rimmask.rim_shares_masks(p, v, 2, zi, 0.5, 0.0)
        ray = rimmask.rim_shares_masks(p, v, 2, zi, 0.5, 0.5)
        assert drill == [1.0, 1.0]
        assert ray[0] == 1.0
        if expect[1] is not None:
            assert ray[1] == expect[1]
        else:
            assert 0.0 < ray[1] < 1.0
