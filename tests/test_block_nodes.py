"""!
@file test_block_nodes.py
@brief Experiment: the metal block as one more layer of the ring network of the Lumped model, against the FVM that has the block.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"))

import block_equivalent_study as study                                         # noqa: E402
from pcbthermal import fvm, lumped                                              # noqa: E402


@pytest.mark.parametrize("rect,pad,thick,k,r_c,fins", [
    ((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4, None),
    ((5, 5, 95, 75), (25, 20, 75, 60), 1.0, 50.0, 2e-3, None),
    ((30, 20, 70, 60), (30, 20, 70, 60), 6.0, 204.0, 1e-4, None),
    ((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4, (15.0, 1.5, 8.0))])
def test_block_nodes_in_the_lumped_model_are_within_6_percent_of_the_fvm(rect, pad, thick, k, r_c, fins):
    p = study.make_case(rect, pad, thick, k, r_c, fins)
    ref = fvm.solve_steady(p, 1.0)
    got = lumped.solve_steady(p, cell_mm=1.0, block_nodes=True)
    assert abs(got.t_max - ref.t_max) < 0.06 * (ref.t_max - 25.0)
    assert got.power_out["blocks"] > 0.15 * got.power_in                          # The block takes a real share of the heat
    with pytest.raises(ValueError, match="metal block"):                           # Off by default
        lumped.solve_steady(p, cell_mm=1.0)
