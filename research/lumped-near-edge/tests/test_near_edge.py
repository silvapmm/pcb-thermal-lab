#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_near_edge.py
@brief Tests of the near-edge investigation: the gap helper, the variants of the Lumped ring construction (anchors, heat balance, behaviour far from an edge) and the image potentials.
@details Run: PCBT_TREE=<checkout of feature/integration-260> QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/lumped-near-edge/tests
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


def test_variants_apply_to_the_program_text():
    """!
    @brief Every variant builds (its anchors are found) in the tree under test.
    @return None.
    """
    for name in ("program", "image", "potlinks", "subcell", "potlinks_subcell"):
        assert V.load(name) is not None


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


@pytest.mark.parametrize("variant", ["program", "potlinks"])
def test_heat_balance_and_centre_behaviour(variant):
    """!
    @brief The network of a variant dissipates the full power (the flux out equals the power) and a centred part reads within 6 % of the program.
    @param variant Variant name.
    @return None.
    """
    p = B.board(100, 80, 5, (50.0, 40.0))
    V.install(variant)
    r = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
    assert sum(r.power_out.values()) == pytest.approx(1.0, rel=2e-3)
    V.install("program")
    ref = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
    assert r.t_max == pytest.approx(ref.t_max, rel=0.06)


def test_potlinks_reduces_the_deficit_at_a_corner():
    """!
    @brief Regression of the headline number: a 10 mm part in a corner of a 100 x 80 board (edge film 10) reads about 22 % cool in the program and within 8 % with the candidate (FVM 0.5 mm).
    @return None.
    """
    pos = (5.0, 5.0)
    p = B.board(100, 80, 10, pos, h_side=10.0)
    f = B.readout(p, "fvm", 0.5, 10, pos)[1]
    V.install("program")
    a = B.readout(p, "lumped", 0.5, 10, pos)[1]
    V.install("potlinks")
    b = B.readout(p, "lumped", 0.5, 10, pos)[1]
    assert a / f - 1 < -0.15
    assert abs(b / f - 1) < 0.08
