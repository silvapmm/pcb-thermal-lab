"""!
@file test_claims.py
@brief The claims of the research as tests: each one is a number the documents quote (CONCLUSIONS.md lists them), checked on small deterministic cases that need only NumPy and SciPy.
@details The reference of every comparison is the mask solved pixel by pixel; the candidates are the mappings of conduction.py. The layouts are written as Gerber text by the tests
         (round tracks and pads from a fixed seed), read by the independent reader and rasterised, so the whole chain (file, reader, mask, mapping, solver) is exercised.
"""

import numpy as np
import pytest

import conduction as cd
import native_gerber as ng
import scenarios as sc

from boards_synthetic import HEAD, mm, random_board_text                  # noqa: E402


def draw(text, size, pix):
    """!
    @brief Rasterise a Gerber text on a square window with the origin at the lower left.
    @param text Gerber text.
    @param size Window side (mm).
    @param pix Pixel size (mm).
    @return Boolean mask, rows from the top.
    """
    cv = ng.Canvas(0.0, size, size, size, pix)
    ng.Layer(text).draw(cv)
    return cv.mask


def test_fill_fraction_is_too_cool_and_flow_based_faces_hold_on_a_random_board():
    """!@brief On a random board with the border held at 0 K the fill fraction is far too cool (claim: 10 to 23 %), the flow-based faces and lambda 0.5 are within a few percent. @return None."""
    mask = draw(random_board_text(), 36.0, 0.1)
    assert 0.15 < mask.mean() < 0.7                                         # a real-looking copper fraction
    S, power, fixed, heater = sc.window_scenario(mask)
    ref, em, ex = sc.compare(S, 0.1, 10, power, fixed, 10.0, heater)
    assert em["fill fraction (today)"] < -8.0
    assert abs(em["flow-based faces"]) < 6.0
    assert abs(em["lambda 0.5"]) < 8.0
    assert abs(em["flow-based faces"]) < abs(em["fill fraction (today)"]) / 2
    assert em["tile method (low bound)"] > 3.0                              # Blackmore's rows-in-parallel bound is too hot on its own


def test_stripes_show_the_direction_effect_that_smearing_misses():
    """!@brief Copper stripes between laminate posts: smearing is far too cool when the heat crosses the stripes and the geometric mean fails along them; the directional mappings stay within 10 %. @return None."""
    S, power, fixed, heater = sc.stripes(pix_mm=0.1, across=True, copper_mm=34.0, stripe_px=5, pitch_px=10)
    _, em, _ = sc.compare(S, 0.1, 10, power, fixed, 0.0, heater)
    assert em["fill fraction (today)"] < -30.0                              # about -49 %: the stripes are a series path across
    assert abs(em["flow-based faces"]) < 10.0 and abs(em["lambda 0.5"]) < 10.0
    S, power, fixed, heater = sc.stripes(pix_mm=0.1, across=False, copper_mm=34.0, stripe_px=5, pitch_px=10)
    _, em, _ = sc.compare(S, 0.1, 10, power, fixed, 0.0, heater)
    assert em["geometric mean"] > 25.0                                      # about +35 %: a scalar cannot be right in both directions
    assert abs(em["flow-based faces"]) < 10.0 and abs(em["lambda 0.5"]) < 10.0
