#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_near_edge.py
@brief Tests of the near-edge investigation: the gap helper, the image potentials, and the heat balance, the centre and the corner on the program as it ships (2.8.0).
@details Run: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/lumped-near-edge/tests. The tests of the source-text variants of lib/variants.py were removed in
         the 2.8.0 reproduction pass: their variants became the program's first link (README, section on 2.8.0).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import gaps as G  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402


def test_gaps_of_a_rectangular_board():
    """!
    @brief The gaps are measured from the polygon to the sides and sorted.
    @return None.
    """
    p = B.board(100, 80, 5, (12.5, 40.0))
    side, g1, g2 = G.gaps_mm(p)[0]
    assert side == pytest.approx(5.0)
    assert g1 == pytest.approx(10.0)
    assert g2 == pytest.approx(37.5)


def test_image_potentials_add_to_the_isolated_ones():
    """!
    @brief With the images the interior potential differences of a footprint at a side differ from the isolated ones; far from every side they agree to a few per cent.
    @return None.
    """
    m = V.load("image")
    cov = np.zeros((160, 200))
    cov[78:82, 98:102] = 1.0
    near = np.zeros_like(cov)
    near[78:82, 0:4] = 1.0
    far_img = m._footprint_potentials(cov, 5e-4, 5e-4)
    far_plain = m._footprint_potentials_plain(cov, 5e-4, 5e-4)
    assert far_img[1] - far_img[0] == pytest.approx(far_plain[1] - far_plain[0], rel=0.15)
    near_img = m._footprint_potentials(near, 5e-4, 5e-4)
    near_plain = m._footprint_potentials_plain(near, 5e-4, 5e-4)
    assert near_img[0] != pytest.approx(near_plain[0], abs=0.05)


def test_heat_balance_and_centre_behaviour():
    """!
    @brief On the program as it ships (first link with the images of the sides, 2.8.0): the Lumped network dissipates the full power and a centred 5 mm part on a 100 x 80 mm
           board reads within 6 % of the FVM (0.5 mm). Measured on development 232ba648: power out 1.000000 W, Lumped 52.483 against FVM 51.981 degC (+1.9 % of the rise).
    @return None.
    """
    p = B.board(100, 80, 5, (50.0, 40.0))
    r = simulate(p, SolverOptions(models=("lumped", "fvm"), cell_mm=0.5)).results
    assert sum(r["lumped"].power_out.values()) == pytest.approx(1.0, rel=2e-3)
    amb = p.board.ambient
    assert (r["lumped"].t_max - amb) == pytest.approx(r["fvm"].t_max - amb, rel=0.06)


def test_corner_deficit_of_the_program():
    """!
    @brief The headline number of the investigation, on the program as it ships: a 10 mm part in a corner of a 100 x 80 board (edge film 10) read about 22 % cool in the
           program of 2.7.1 and within 8 % with the candidate `potlinks`; the program of 2.8.0 (fix/lumped-edge-first-link, from research/lumped-edge-link) reads it within 8 %
           of the FVM (0.5 mm). Measured on development 232ba648: hottest node FVM 47.359 K, Lumped 46.349 K, -2.13 %.
    @return None.
    """
    pos = (5.0, 5.0)
    p = B.board(100, 80, 10, pos, h_side=10.0)
    f = B.readout(p, "fvm", 0.5, 10, pos)[1]
    a = B.readout(p, "lumped", 0.5, 10, pos)[1]
    assert abs(a / f - 1) < 0.08
