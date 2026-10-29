"""!
@file test_calculator_validation.py
@brief The power calculator against datasheets: on the datasheet's own board the model must return the datasheet's thermal resistance.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "power-calculator", "scripts"))

import calculator_validation as cv                                          # noqa: E402


def test_csd17308q3_datasheet_board_gives_its_typical_rtheta_ja():
    """TI CSD17308Q3: RθJA typical 46 K/W on 1 in² of 2 oz copper. The calculator returns 1 W within 3 % when the junction is 46 K above ambient."""
    out = cv.recovered(cv.csd17308q3_board(), 46.0, cell_mm=0.5)
    assert out["power_w"] == pytest.approx(1.0, abs=0.03)
    assert 44.0 < 46.0 / out["power_w"] < 48.5                                  # The model's RθJA on that board, K/W


def test_jedec_2s2p_exposed_pad_board_is_within_5_percent_of_a_tps7a47_like_rtheta_ja():
    """A JESD51-7 2s2p board with 9 thermal vias under a 3.15 mm exposed pad and θJC(bot) 1.7 K/W (assumed package): the calculator returns 1 W within 5 % for
    RθJA 32.5 K/W, from the junction and from the top with ψJT 0.3 K/W."""
    for point, psi in (("junction", 0.0), ("top", 0.3)):
        out = cv.recovered(cv.jedec_2s2p_board(), 32.5, cell_mm=1.0, point=point, psi_jt=psi)
        assert out["power_w"] == pytest.approx(1.0, abs=0.05), point


def test_the_thermal_vias_are_what_the_jedec_board_needs():
    """Without the vias under the pad the same package on the same board is about twice as hot per watt: the exposed pad needs them (JESD51-5)."""
    with_vias = cv.recovered(cv.jedec_2s2p_board(vias=True), 32.5, cell_mm=1.0)["power_w"]
    without = cv.recovered(cv.jedec_2s2p_board(vias=False), 32.5, cell_mm=1.0)["power_w"]
    assert without < 0.6 * with_vias
