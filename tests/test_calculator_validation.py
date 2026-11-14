#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
    """TI CSD17308Q3: RθJA typical 46 K/W on 1 in² of 2 oz copper. The calculator returns 1 W within 0.04 W (4 %) when the junction is 46 K above ambient."""
    out = cv.recovered(cv.csd17308q3_board(), 46.0, cell_mm=0.5)
    assert out["power_w"] == pytest.approx(1.0, abs=0.04)                       # 0.986 W on 2.6.0 and 2.7.0 (0.968 W with the laminate nodes of 2.4.5 and the face-down law of 2.5; docs/calculators.md 2.1)
    assert 44.0 < 46.0 / out["power_w"] < 48.5                                  # The model's RθJA on that board, K/W


def test_jedec_2s2p_board_as_drawn_keeps_the_programs_own_value():
    """Regression of the program, NOT a validation: the board as drawn (no backside copper, vias joined to every layer) differs from the board of ROHM 64AN113E, and the
    four readings of it span 27.6 to 36.1 K/W (docs/calculators.md 2.1). The model RθJA of this board at 1 mm was 32.23 K/W on the tree of the audit (31.59 at 0.5 mm);
    the band is narrow so that a model change that moves it is noticed (re-take the value, and say why, when the copper faces of a drawn board change).
    The datasheet's 32.5 K/W is one reading among several, so no agreement with it is asserted."""
    for point, psi in (("junction", 0.0), ("top", 0.3)):
        out = cv.recovered(cv.jedec_2s2p_board(), 32.5, cell_mm=1.0, point=point, psi_jt=psi)
        assert 32.5 / out["power_w"] == pytest.approx(32.23, abs=0.3), point


def test_jedec_board_readings_keep_their_order():
    """The order of the four readings of the JEDEC board at 1 mm (light version of study_jedec_board_readings.py): the backside plane cools (B lowest), a layer 3 that
    the vias do not join warms (C above B), the board as drawn is above both, and no backside plane with the layer cut is the hottest (D). Model RθJA in K/W: B 27.5,
    C 28.3, A 32.2, D 36.5 on the tree of the audit."""
    import study_jedec_board_readings as study
    r = {name: 32.5 / cv.recovered(study.board(bottom, joined), 32.5, cell_mm=1.0)["power_w"]
         for name, bottom, joined in (("A", False, True), ("B", True, True), ("C", True, False), ("D", False, False))}
    assert r["B"] < r["C"] < r["A"] < r["D"], r
    assert 27.0 < r["B"] and r["D"] < 38.0                                       # The span stays near the 27.6 to 36.1 K/W of the audit (0.5 mm)


def test_the_thermal_vias_are_what_the_jedec_board_needs():
    """Without the vias under the pad the same package on the same board is about twice as hot per watt: the exposed pad needs them (JESD51-5)."""
    with_vias = cv.recovered(cv.jedec_2s2p_board(vias=True), 32.5, cell_mm=1.0)["power_w"]
    without = cv.recovered(cv.jedec_2s2p_board(vias=False), 32.5, cell_mm=1.0)["power_w"]
    assert without < 0.6 * with_vias
