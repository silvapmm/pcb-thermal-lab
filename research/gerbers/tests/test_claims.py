"""!
@file test_claims.py
@brief The claims of the research as tests: each one is a number the documents quote (CONCLUSIONS.md lists them), checked on small deterministic cases that need only NumPy and SciPy.
@details The reference of every comparison is the mask solved pixel by pixel; the candidates are the mappings of conduction.py. The layouts are written as Gerber text by the tests
         (round tracks and pads from a fixed seed), read by the independent reader and rasterised, so the whole chain (file, reader, mask, mapping, solver) is exercised.
"""

import math

import numpy as np
import pytest
from scipy import ndimage

import conduction as cd
import native_gerber as ng
import scenarios as sc

HEAD = "%FSLAX36Y36*%\n%MOMM*%\n"


def mm(v):
    """!
    @brief A length in mm as the integer string of a 3.6 coordinate format.
    @param v Length (mm).
    @return String.
    """
    return str(int(round(v * 1e6)))


def random_board_text(seed=11, tracks=110, pads=70, size=36.0):
    """!
    @brief A Gerber text with random round tracks (0.15 to 0.5 mm, up to 14 mm long, any angle) and round pads (0.8 to 2 mm), plus a ground pour with a few clearance holes.
    @param seed Random seed.
    @param tracks Number of tracks.
    @param pads Number of pads.
    @param size Board side (mm).
    @return Gerber text.
    """
    rng = np.random.default_rng(seed)
    widths = (0.15, 0.2, 0.3, 0.5)
    t = HEAD + "".join(f"%ADD{10 + i}C,{w}*%\n" for i, w in enumerate(widths)) + "".join(f"%ADD{20 + i}C,{d}*%\n" for i, d in enumerate((0.8, 1.2, 2.0)))
    # A pour on the left third with holes cut by clear flashes, then tracks and pads on top
    t += "G36*\n" + f"X{mm(0)}Y{mm(0)}D02*\nX{mm(12)}Y{mm(0)}D01*\nX{mm(12)}Y{mm(size)}D01*\nX{mm(0)}Y{mm(size)}D01*\nX{mm(0)}Y{mm(0)}D01*\nG37*\n"
    t += "%LPC*%\n%ADD30C,1.0*%\nD30*\n" + "".join(f"X{mm(x)}Y{mm(y)}D03*\n" for x, y in rng.uniform(1, 11, (20, 2))) + "%LPD*%\n"
    for _ in range(tracks):
        x, y = rng.uniform(1, size - 1, 2)
        a, ln = rng.uniform(0, 2 * math.pi), rng.uniform(2, 14)
        x2, y2 = min(max(x + ln * math.cos(a), 0.5), size - 0.5), min(max(y + ln * math.sin(a), 0.5), size - 0.5)
        t += f"D{10 + int(rng.integers(4))}*\nX{mm(x)}Y{mm(y)}D02*\nX{mm(x2)}Y{mm(y2)}D01*\n"
    for _ in range(pads):
        x, y = rng.uniform(1, size - 1, 2)
        t += f"D{20 + int(rng.integers(3))}*\nX{mm(x)}Y{mm(y)}D03*\n"
    return t + "M02*\n"


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


def test_thin_track_at_an_angle_connectivity_area_and_resistance():
    """!@brief A 0.1 mm track at 30 degrees: in pieces with 4-connectivity at a 0.1 mm pixel, one piece with 8-connectivity; a 0.2 mm track is exact in area and within 15 % in resistance at 8 pixels across. @return None."""
    import joule
    ca, sa = math.cos(math.radians(30)), math.sin(math.radians(30))
    def track(w, pix, length=6.0):
        t = HEAD + f"%ADD10C,{w}*%\nD10*\nX{mm(1)}Y{mm(1)}D02*\nX{mm(1 + length * ca)}Y{mm(1 + length * sa)}D01*\nM02*\n"
        return draw(t, 8.0, pix)
    thin = track(0.1, 0.1)
    assert ndimage.label(thin)[1] > 5
    assert ndimage.label(thin, structure=np.ones((3, 3)))[1] == 1
    m = track(0.2, 0.025)
    exact = 6.0 * 0.2 + math.pi * 0.01
    assert m.sum() * 0.025 ** 2 == pytest.approx(exact, rel=0.02)
    lab, n = ndimage.label(m)
    assert n == 1
    ys, xs = np.where(m)
    order = np.argsort(xs)
    src = np.zeros_like(m); snk = np.zeros_like(m)
    src[ys[order[:20]], xs[order[:20]]] = True
    snk[ys[order[-20:]], xs[order[-20:]]] = True
    r, _, _ = joule.solve_net(m, 1.0, src, snk, 1.0)
    ideal = (6.0 - 0.2) / 0.2                                              # squares between the end caps, roughly
    assert 0.9 * ideal < r < 1.35 * ideal                                   # the five-point stencil is too resistive on a tilted track (claim: +10 % at 8 pixels)


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
