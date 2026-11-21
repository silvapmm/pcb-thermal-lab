#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_harness_rows.py
@brief Regression test of the harness study: the rule-F offset of a part is read on that part's own footprint, not on the footprint of every part of its layer.
@details The first version of study_harness_boards.py masked the rule-F offset with `q_src > 0` of the whole layer, so on a board with two parts on one face both rows read the
         hottest offset of the layer (U1 and U2 of the example board both printed 1.37 mK). The review fixed the mask; this test holds it.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import study_harness_boards as SH  # noqa: E402


def test_rule_f_offset_is_read_per_part():
    # The example board at a coarse cell: two parts on the top face with different power densities
    rows = {r["part"]: r for r in SH.run_board("example_board", 4.0)}
    assert {"U1", "U2"} <= set(rows)
    for m in ("d_lumped", "d_analytic"):
        a, b = rows["U1"][m], rows["U2"][m]
        assert np.isfinite(a) and np.isfinite(b)
        assert abs(a - b) > 1e-6, f"{m}: the two parts read the same offset ({a}, {b}): the mask is the layer's, not the part's"
        # Each offset stays below the part's own bound q'' t / 2k (an outer face of 35 um copper: every term is within it)
        for r in (rows["U1"], rows["U2"]):
            assert r[m] <= r["bound_k"] * (1 + 1e-9)
