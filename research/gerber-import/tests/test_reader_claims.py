"""!
@file test_reader_claims.py
@brief Claims about reading and rasterising (phase 1), as tests: the net of a thin wire, and a track as wide as the pixel.
@details Small deterministic cases written as Gerber text and read by the independent reader; NumPy and SciPy only.
"""

import numpy as np
from scipy import ndimage

import native_gerber as ng
from boards_synthetic import HEAD, mm


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


def test_net_pieces_are_found_by_connectivity_and_a_thin_wire_keeps_its_net():
    """!@brief Two nets drawn as pads joined by a thin diagonal wire: the labelled pieces carry one net each, and the wire joins its pads with 8-connectivity at a pixel as wide as the wire. @return None."""
    t = (HEAD + "%ADD10C,0.1*%\n%ADD11C,1.0*%\n%TO.N,5V*%\nD11*\n" + f"X{mm(2)}Y{mm(2)}D03*\nX{mm(8)}Y{mm(5)}D03*\nD10*\nX{mm(2)}Y{mm(2)}D02*\nX{mm(8)}Y{mm(5)}D01*\n"
         "%TO.N,GND*%\nD11*\n" + f"X{mm(2)}Y{mm(8)}D03*\nX{mm(8)}Y{mm(8)}D03*\nD10*\nX{mm(2)}Y{mm(8.03)}D02*\nX{mm(8)}Y{mm(8.03)}D01*\n%TD*%\nM02*\n")
    layer = ng.Layer(t)
    assert layer.net_names() == ["5V", "GND"]
    cv = ng.Canvas(0.0, 10.0, 10.0, 10.0, 0.1)
    layer.draw(cv)
    lab, n = ndimage.label(cv.mask, structure=np.ones((3, 3)))
    assert n == 2                                                           # the wire keeps each pair of pads in one piece
    owners = []
    for net in layer.net_names():
        c = ng.Canvas(0.0, 10.0, 10.0, 10.0, 0.1)
        layer.draw(c, [net])
        owners.append(set(np.unique(lab[c.mask & (lab > 0)]).tolist()))
    assert all(len(o) == 1 for o in owners) and owners[0] != owners[1]


def test_a_track_as_wide_as_the_pixel_can_vanish_on_the_lattice():
    """!@brief A 0.1 mm wire whose edges lie exactly on pixel centres of a 0.1 mm lattice is not drawn at all (centre sampling tie), at half the pixel it is: the rule "pixel at most half the thinnest track". @return None."""
    t = HEAD + "%ADD10C,0.1*%\n%ADD11C,1.0*%\nD11*\n" + f"X{mm(2)}Y{mm(8)}D03*\nX{mm(8)}Y{mm(8)}D03*\nD10*\nX{mm(2)}Y{mm(8)}D02*\nX{mm(8)}Y{mm(8)}D01*\nM02*\n"
    for pix, pieces in ((0.1, 2), (0.05, 1)):
        m = draw(t, 10.0, pix)
        assert ndimage.label(m, structure=np.ones((3, 3)))[1] == pieces

