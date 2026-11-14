#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_study_block_pads.py
@brief The synthetic board builder of the block-pads study: pad and part counts, the control board without a block, and the power split.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import study_block_pads as s                                         # noqa: E402


def test_builder_counts_and_power():
    """!
    @brief Four pads give four parts and zones on the bottom, the total power is kept and the control has no block.
    @return None.
    """
    p = s.make(n_pads=4)
    assert len(p.heaters) == 4 and len(p.heatsinks) == 1
    assert abs(sum(h.power for h in p.heaters) - 5.0) < 1e-12
    assert len(s.make(n_pads=2, with_block=False).heatsinks) == 0


def test_lumped_part_is_read_with_its_own_peak():
    """!
    @brief The review's definition check: on a one-part board the Lumped own peak of the part equals its t_max, while the field under the footprint reads lower (the node).
    @return None.
    """
    from pcbthermal import lumped
    p = s.make(n_pads=1)
    s._CAPTURED.clear()
    r = lumped.solve_steady(p, cell_mm=2.0)
    own = s.lumped_part_peaks(p, r)
    assert abs(own[0] - (r.t_max - s.AMB)) < 1e-9
    field = s.metrics("lumped", p, 2.0)
    assert field["parts"][0] < field["parts_own"][0] - 1.0         # the painted footprint node lacks the peak term (several kelvin here)
