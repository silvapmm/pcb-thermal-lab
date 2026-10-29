#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_outline.py
@brief The board outline read from a profile layer (README 4.47): a rounded rectangle with a slot against its exact areas, a contour with a gap flagged as open, and a zero-width aperture.
@details The exact areas follow from the geometry: a 40 x 30 mm board with corners of 3 mm radius drawn with a stroke of 0.1 mm has the area of its centre-line shape less half the stroke on every side; a slot of 10 x 4 mm takes the area of its outer edge (10.1 x 4.1 mm). Needs gerbonara and shapely only because the synthetic files are written by study_outline.py.
"""

import math

import pytest

pytest.importorskip("gerbonara")
pytest.importorskip("shapely")

import outline
import study_outline as so

PIX = 0.05
WINDOW = (-0.5, 30.5, 41.0, 31.0)


def read(text):
    """!
    @brief Run the outline reader on a Gerber text.
    @param text Gerber text of a profile layer.
    @return tuple (board mask, closed flag, polygons).
    """
    strokes = outline.stroke_mask(outline.prepare(text, PIX), WINDOW, PIX)
    mask, closed, _ = outline.board_mask(strokes)
    return mask, closed, outline.polygons(mask, WINDOW, PIX)


def test_rounded_rectangle_area_and_polygon():
    """!@brief The board region of the rounded rectangle has the area of its centre-line shape less half the stroke on each side, and the polygon one outer contour (the inner edge of the stroke band: the cut is half a stroke further out). @return None."""
    mask, closed, polys = read(so.synthetic("rounded"))
    centre = 40.0 * 30.0 - (4 - math.pi) * 3.0 ** 2
    perimeter = 2 * (34.0 + 24.0) + 2 * math.pi * 3.0
    assert closed
    assert abs(mask.sum() * PIX ** 2 - (centre - 0.05 * perimeter)) < 1.0
    assert len(polys) == 1 and abs(outline.area(polys[0]) - mask.sum() * PIX ** 2) < 2.0       # the polygon is the inner edge of the stroke band


def test_slot_is_a_cut_out():
    """!@brief With a slot the board loses the slot's outer area (10.1 x 4.1 mm) and the polygons are the board and one hole. @return None."""
    mask, closed, polys = read(so.synthetic("slot"))
    rounded, _, _ = read(so.synthetic("rounded"))
    assert closed
    assert abs((rounded.sum() - mask.sum()) * PIX ** 2 - 10.1 * 4.1) < 1.0
    assert len(polys) == 2 and abs(outline.area(polys[1]) - 10.1 * 4.1) < 1.0


def test_a_gap_is_reported_as_open_and_overlapping_ends_are_not_a_gap():
    """!@brief A gap of 0.2 mm in the contour is flagged as not closed, a gap of 0.05 mm (the round ends of a 0.1 mm stroke overlap) is read as closed. @return None."""
    assert not read(so.synthetic("gap0.2"))[1]
    assert not read(so.synthetic("gap0.5"))[1]
    assert read(so.synthetic("gap0.05"))[1]


def test_zero_width_aperture_is_widened():
    """!@brief A profile drawn with a zero-width aperture is widened to one and a half pixel and then read like any other. @return None."""
    text = so.synthetic("rounded").replace("%ADD10C,0.1*%", "%ADD10C,0*%")
    assert "C,0*" in text
    mask, closed, _ = read(text)
    assert closed and mask.sum() * PIX ** 2 > 1150.0
