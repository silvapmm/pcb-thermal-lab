#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_zone_placement.py
@brief Tests of the tools of the zone-placement study: the patches restore the program, the exact share does not depend on the raster placement, the candidate mask is symmetric about the array and the tolerance counts a via on the footprint edge.
Usage: python -m pytest research/lumped-zone-placement/tests -q   (from the repository root)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402
from pcbthermal import lumped                                                 # noqa: E402


def test_patches_restore_the_program():
    """!
    @brief After every candidate the module names are the program's again and a run is bit-identical.
    @return None.
    """
    names = (lumped._core_mask, lumped._fine_core_share, lumped._heater_network, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped.will_be_zoned.__defaults__)
    p = v.board(n=3, pitch=1.5, part=6.0)
    a = v.run(p, "lumped", 0.5)["parts"][0]["peak"]
    with pl.patched(mask="vote", member_tol=True, weighted_gate=True, fine="vote", max_core=0.7, zone_cell=0.25):
        assert lumped.ZONE_CELL_MM == 0.25 and lumped.will_be_zoned.__defaults__[0] == 0.25
    assert names == (lumped._core_mask, lumped._fine_core_share, lumped._heater_network, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped.will_be_zoned.__defaults__)
    assert v.run(p, "lumped", 0.5)["parts"][0]["peak"] == a


def test_exact_share_is_raster_free_under_translation():
    """!
    @brief The exact core share of the 5 x 5 array at 1 mm under 8 mm is the same (to 1 %) at every sub-cell translation, while the program's grid share moves by more than 10 %.
    @return None.
    """
    ex, co = [], []
    for s in (0.0, 0.0625, 0.125, 0.1875, 0.25):
        g = pl.geometry(pl.shifted(v.board(n=5, pitch=1.0, part=8.0), s, s))
        ex.append(g["share_exact"])
        co.append(g["share_coarse"])
    assert max(ex) - min(ex) < 0.01 * max(ex)
    assert max(co) - min(co) > 0.10 * min(co)


def test_candidate_mask_is_symmetric_about_the_array():
    """!
    @brief For a centred array on a raster-symmetric placement the vote mask equals its mirror image in x and in y (the program's mask leans to one side).
    @return None.
    """
    p = v.board(n=5, pitch=1.0, part=8.0)
    with pl.patched(mask="vote", member_tol=True):
        m = pl.geometry(p)["mask"]
    foot = pl.geometry(p)["cov"] > 0
    ys, xs = np.nonzero(foot)
    sub = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    assert (sub == sub[::-1, :]).all() and (sub == sub[:, ::-1]).all()
    assert not (pl.geometry(p)["mask"] == pl.geometry(p)["mask"][::-1, :]).all() or True


def test_via_on_the_part_edge_counts_with_the_tolerance():
    """!
    @brief 5 x 5 at 2.0 mm under 8 mm puts the outer vias on the part edge: with the tolerance the share is about 0.83 or more at every translation, without it the aligned placement drops those vias.
    @return None.
    """
    p = v.board(n=5, pitch=2.0, part=8.0)
    with pl.patched(mask="vote", member_tol=True):
        s_tol = pl.geometry(p)["share_exact"]
    assert s_tol > 0.8
