"""!
@file test_geometry.py
@brief The Gerber reader on tiny synthetic files written by the test: areas, polarity, holes and the centre-sampled mask.
"""

import math

import numpy as np
import pytest

pytest.importorskip("gerbonara")
pytest.importorskip("shapely")

import gerber_geometry as gg

GERBER = """%FSLAX36Y36*%
%MOMM*%
%ADD10C,1.000*%
%ADD11C,0.200*%
%ADD12R,2.000X1.000*%
G01*
%LPD*%
D10*
X5000000Y5000000D03*
D11*
X0Y10000000D02*
X10000000Y10000000D01*
D12*
X20000000Y5000000D03*
M02*
"""

GERBER_CLEAR = """%FSLAX36Y36*%
%MOMM*%
%ADD10R,10.000X10.000*%
%ADD11C,2.000*%
G01*
%LPD*%
D10*
X5000000Y5000000D03*
%LPC*%
D11*
X5000000Y5000000D03*
M02*
"""

DRILL = """M48
METRIC,TZ
T1C0.800
T2C1.000
%
T1
X10.0Y20.0
X11.5Y20.0
T2
X30.0Y40.0
M30
"""


def write(tmp_path, name, text):
    """!
    @brief Write a small text file.
    @param tmp_path Temporary directory.
    @param name File name.
    @param text Content.
    @return Path of the file.
    """
    p = tmp_path / name
    p.write_text(text)
    return p


def test_areas_of_draw_flash_and_rectangle(tmp_path):
    """!@brief A round flash, a stroke with round caps and a rectangle flash add up to their analytic area. @param tmp_path pytest temp dir. @return None."""
    geom, stats = gg.load_copper(write(tmp_path, "a.gbr", GERBER))
    expected = math.pi * 0.5 ** 2 + (10.0 * 0.2 + math.pi * 0.1 ** 2) + 2.0 * 1.0
    assert stats["primitives"] == 3 and stats["clear"] == 0
    assert geom.area == pytest.approx(expected, rel=0.01)


def test_clear_polarity_makes_a_hole(tmp_path):
    """!@brief A clear flash inside a dark one removes its area and leaves a real hole. @param tmp_path pytest temp dir. @return None."""
    geom, stats = gg.load_copper(write(tmp_path, "c.gbr", GERBER_CLEAR))
    assert stats["clear"] == 1
    assert geom.area == pytest.approx(100.0 - math.pi, rel=0.01)
    assert len(geom.interiors) == 1


def test_mask_matches_the_exact_area_and_the_hole(tmp_path):
    """!@brief The centre-sampled mask reproduces the area to a fraction of a percent and shows the hole as empty pixels. @param tmp_path pytest temp dir. @return None."""
    geom, _ = gg.load_copper(write(tmp_path, "c.gbr", GERBER_CLEAR))
    m = gg.sample_mask(geom, 0.0, 10.0, 10.0, 10.0, 0.05)
    assert m.shape == (200, 200)
    assert m.sum() * 0.05 ** 2 == pytest.approx(geom.area, rel=0.01)
    assert m[100, 100] == 0 and m[10, 10] == 1                       # hole in the middle, copper near the corner


def test_antialiased_mask_is_fractional_at_the_edge(tmp_path):
    """!@brief With 4 x 4 samples per pixel, a pixel cut by an edge has a fraction between 0 and 1 and the total area is closer to the exact one. @param tmp_path pytest temp dir. @return None."""
    geom, _ = gg.load_copper(write(tmp_path, "c.gbr", GERBER_CLEAR))
    plain = gg.sample_mask(geom, 0.0, 10.0, 10.0, 10.0, 0.3, 1)
    aa = gg.sample_mask(geom, 0.0, 10.0, 10.0, 10.0, 0.3, 4)
    assert ((aa > 0) & (aa < 1)).any() and not ((plain > 0) & (plain < 1)).any()
    assert abs(aa.sum() * 0.09 / geom.area - 1) <= abs(plain.sum() * 0.09 / geom.area - 1) + 1e-9


def test_drill_holes(tmp_path):
    """!@brief An Excellon file gives its holes with position and diameter. @param tmp_path pytest temp dir. @return None."""
    holes = gg.drill_holes(write(tmp_path, "d.drl", DRILL))
    assert len(holes) == 3
    assert sorted(round(h[2], 2) for h in holes) == [0.8, 0.8, 1.0]
    assert any(abs(h[0] - 30.0) < 1e-6 and abs(h[1] - 40.0) < 1e-6 for h in holes)
