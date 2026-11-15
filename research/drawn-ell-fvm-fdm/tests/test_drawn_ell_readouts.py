#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_drawn_ell_readouts.py
@brief The numbers of the README of research/drawn-ell-fvm-fdm: the heater mean agrees across models, the board maximum at 1 mm differs, both on the program of this tree.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import study_readouts as S      # noqa: E402

REF_MEAN = 63.8     # K, independent FEM with a graded mesh (study_graded_fem.py: 63.644, 63.763, 63.807)


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_heater_mean_agrees_with_the_reference_at_1_mm(model):
    """!
    @brief The heater mean is within 5 % of the independent finite-element value in both models.
    @param model "fvm" or "fdm".
    @return None.
    """
    r = S.run_one("drawn_ell", model, 1.0)
    assert abs(r["h_mean"] - REF_MEAN) / REF_MEAN < 0.05


def test_board_maximum_at_1_mm_is_the_reported_gap():
    """!
    @brief The reviewer's numbers: FVM 99.0 K and FDM 67.0 K at 1 mm (so a change of either moves this test on purpose).
    @return None.
    """
    assert S.run_one("drawn_ell", "fvm", 1.0)["tmax"] == pytest.approx(99.035, abs=0.05)
    assert S.run_one("drawn_ell", "fdm", 1.0)["tmax"] == pytest.approx(66.955, abs=0.05)
