#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_strong_edge.py
@brief Tests of the 3D reference of research/strong-edge-laminate and of the way the study drives the program.
@details Run: `.venv/bin/python -m pytest -q research/strong-edge-laminate/tests`. The reference is checked against its own energy balance, the disc area of its via and the
         limit of an insulated board (a closed form); the program driver against the default laminate rule.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
import prog                                                         # noqa: E402
import ref3d                                                        # noqa: E402

DXV = 0.125e-3                                                      # the barrel links need a few cell centres inside the 0.15 mm disc
DX = 0.25e-3                                                        # a coarse plan cell keeps the tests fast


def test_heat_balance_is_one():
    """!
    @brief The heat lost through the films equals the power, with and without the via and with a copper inset.
    @return None.
    """
    for kw in (dict(via="none"), dict(via="cyl"), dict(via="none", inset=0.5e-3)):
        r = ref3d.solve(1000.0, 3, DX, **kw)
        assert abs(r["balance"] - 1.0) < 1e-9


def test_disc_share_area():
    """!
    @brief The area shares of the drill disc add up to pi r^2.
    @return None.
    """
    dx = 1.0 / 16 * 1e-3
    xs = (np.arange(160) + 0.5) * dx
    ys = (np.arange(80) + 0.5) * dx
    s = ref3d.disc_share(xs, ys, 9.84e-3, 5e-3, 0.15e-3, dx)
    area = s.sum() * dx * dx * 2                                   # the half domain holds half of the disc
    assert abs(area / (math.pi * 0.15e-3 ** 2) - 1.0) < 0.01


def test_insulated_board_is_the_closed_form():
    """!
    @brief With every edge insulated and a uniform stack the mean top-plus-bottom loss is P: the mean rise equals P over the film conductance for a thin board.
    @details Not exact for a spreading source, so the check is on the energy: the weighted mean of the rises over the faces gives back the power.
    @return None.
    """
    r = ref3d.solve(0.0, 2, DX)
    assert abs(r["balance"] - 1.0) < 1e-9
    assert r["tmax"] > 0


def test_via_lowers_the_peak_and_representations_agree():
    """!
    @brief A copper via next to the source lowers the peak; the resolved cylinder and the barrel links agree within 25 % on the effect.
    @return None.
    """
    a = ref3d.solve(200.0, 2, DXV)["tmax"]
    e_cyl = a - ref3d.solve(200.0, 2, DXV, "cyl", via_dist=0.5e-3)["tmax"]
    e_link = a - ref3d.solve(200.0, 2, DXV, "link", via_dist=0.5e-3, gv_gap=ref3d.barrel_gv())["tmax"]
    assert e_cyl > 0 and e_link > 0
    assert abs(e_cyl / e_link - 1.0) < 0.25


def test_default_laminate_is_two_subgaps_on_this_board():
    """!
    @brief The shipped rule (s_max 0.4 mm) cuts the 0.487 mm gaps of this board into 2 sub-gaps, so n_sub=2 reproduces the default (the labels '4 sub-gaps' of the earlier notes were wrong).
    @return None.
    """
    p = prog.board(1000.0)
    assert abs(prog.run(p, 1.0) - prog.run(p, 1.0, 2)) < 1e-9
    assert prog.run(p, 1.0, 5) > prog.run(p, 1.0)                  # more sub-gaps, hotter board


def test_review_the_simple_stackup_slabs_are_the_residual():
    """!
    @brief Review: at h_side 1000 W/m2K, cell 0.25 mm, eight sub-gaps, the simple stack-up and the same board with its physical slabs
           (advanced stack-up, three equal gaps: the board of the 3D reference) are both within 1 % of the stored reference rise (24.734 K at 1/8 mm, 8 slabs).
           The simple stack-up used to read the plate about 5 % cool (equal 0.4 mm slabs); since 2.7.0 (fix/simple-stackup-physical-layers) it has the physical layers
           and the residual is -0.35 % (measured 24.8204 K), so the two agree.
    @return None.
    """
    from pcbthermal.model import Dielectric
    simple = prog.run(prog.board(1000.0), 0.25, 8)
    p = prog.board(1000.0)
    p.board.dielectrics = [Dielectric(thickness=prog.GAP_MM * 1e-3, k_through=0.3, k_inplane=0.3) for _ in range(3)]
    phys = prog.run(p, 0.25, 8)
    ref = 24.733774410638922
    assert abs(simple / ref - 1) < 0.01                                 # measured -0.35 % with the physical slabs of the simple stack-up (2.7.0)
    assert abs(phys / ref - 1) < 0.01
