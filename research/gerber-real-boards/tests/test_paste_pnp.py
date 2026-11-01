#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_paste_pnp.py
@brief Tests of the paste groups (by reference designator and by proximity), the click, the placement files and their registration, and the X3 component layer, all on small synthetic files written here (no download).
"""

import numpy as np
import pytest

import paste
import pnp
import x3

PASTE = """%FSLAX36Y36*%
%MOMM*%
%ADD10R,1.000000X0.500000*%
%ADD11R,3.000000X3.000000*%
%LPD*%
G01*
D10*
%TO.C,R1*%
X10000000Y10000000D03*
X11500000Y10000000D03*
%TD*%
D11*
%TO.C,U1*%
X20000000Y20000000D03*
%TD*%
M02*
"""


@pytest.fixture
def paste_file(tmp_path):
    """!@brief A synthetic paste file with two parts. @param tmp_path pytest folder. @return Path."""
    p = tmp_path / "paste.gbr"
    p.write_text(PASTE)
    return p


def test_reference_text_rewrites_component_attribute():
    """!@brief TO.C becomes TO.N so that the reader keeps the reference per object. @return None."""
    assert "%TO.N,R1*%" in paste.reference_text("%TO.C,R1*%")


def test_by_reference_finds_parts_and_centres(paste_file):
    """!@brief The two references are found with the right centre and area. @param paste_file fixture. @return None."""
    g = paste.by_reference(paste_file, pix=0.025)
    assert set(g) == {"R1", "U1"}
    assert abs(g["R1"]["x"] - 10.75) < 0.05 and abs(g["R1"]["y"] - 10.0) < 0.05
    assert abs(g["R1"]["area"] - 1.0) < 0.1                 # two pads of 1.0 x 0.5 mm
    assert abs(g["U1"]["area"] - 9.0) < 0.2


def test_by_proximity_link_distance(paste_file):
    """!@brief Pads 0.5 mm apart are two groups at link 0.3 and one group at link 0.6. @param paste_file fixture. @return None."""
    box = (0.0, 0.0, 30.0, 30.0)
    assert len(paste.by_proximity(paste_file, box, pix=0.05, link_mm=0.3)) == 3
    two = paste.by_proximity(paste_file, box, pix=0.05, link_mm=0.6)
    assert len(two) == 2
    r1 = min(two, key=lambda g: g["x"])
    assert len(r1["pads"]) == 2


def test_shapes_and_pick(paste_file):
    """!@brief The candidate footprints of a group and the click that picks it. @param paste_file fixture. @return None."""
    groups = paste.by_proximity(paste_file, (0.0, 0.0, 30.0, 30.0), pix=0.05, link_mm=0.6)
    r1 = min(groups, key=lambda g: g["x"])
    s = paste.shapes(r1)
    assert set(s) >= {"bbox", "largest"}
    assert s["bbox"]["area"] > s["largest"]["area"]
    i = paste.pick(groups, 10.75, 10.0)
    assert groups[i] is r1
    assert paste.pick(groups, 100.0, 100.0) is None         # a click far from every group picks nothing


CSV_KICAD = "Ref,Val,Package,PosX,PosY,Rot,Side\n\"C1\",\"100n\",\"C_0402\",-34.395,-49.053,180.0,bottom\n\"R1\",\"10k\",\"R_0402\",10.0,5.0,90.0,top\n"
CSV_JLC = "Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\nC13,100n,C_0402,-34.395,-49.053,180,bottom\n"
CSV_ALTIUM = "Designator,Footprint,Mid X,Mid Y,Layer,Rotation\nU1,QFN32,1000mil,500mil,Top,270\n"
POS_TEXT = "## Footprint positions - created on 2026\n## Side : All\n# Ref     Val        Package          PosX       PosY       Rot  Side\nC1     100n    C_0402    -34.395   -49.053   180.0  bottom\nR1     10k     R_0402     10.000     5.000    90.0  top\n## End\n"


def test_read_placement_variants(tmp_path):
    """!@brief KiCad CSV, JLCPCB CSV, Altium CSV with unit suffixes and the KiCad text format all read. @param tmp_path pytest folder. @return None."""
    for name, text in (("k.csv", CSV_KICAD), ("j.csv", CSV_JLC), ("a.csv", CSV_ALTIUM), ("k.pos", POS_TEXT)):
        (tmp_path / name).write_text(text)
    k = pnp.read_placement(tmp_path / "k.csv")
    assert k[0]["ref"] == "C1" and k[0]["side"] == "bottom" and k[1]["rot"] == 90.0
    j = pnp.read_placement(tmp_path / "j.csv")
    assert j[0]["ref"] == "C13" and abs(j[0]["x"] + 34.395) < 1e-9
    a = pnp.read_placement(tmp_path / "a.csv")
    assert abs(a[0]["x"] - 25.4) < 1e-9 and abs(a[0]["y"] - 12.7) < 1e-9 and a[0]["side"] == "top"
    t = pnp.read_placement(tmp_path / "k.pos")
    assert [p["ref"] for p in t] == ["C1", "R1"] and t[0]["side"] == "bottom"


def test_register_recovers_shift_and_flip():
    """!@brief A placement list shifted and with Y flipped is put back on the group centres. @return None."""
    rng = np.random.default_rng(1)
    g = rng.uniform(0, 80, size=(60, 2))
    placement = g * np.array([1, -1]) - np.array([30.0, -12.0])         # the file has Y up the other way and another origin
    tr = pnp.register(g, placement, tol_mm=0.2)
    assert tr["sx"] == 1 and tr["sy"] == -1
    assert tr["matched"] == 60 and tr["median_mm"] < 0.05
    x, y = pnp.apply(tr, placement[3, 0], placement[3, 1])
    assert abs(x - g[3, 0]) < 0.05 and abs(y - g[3, 1]) < 0.05


def test_register_with_no_points():
    """!@brief An empty input gives an empty match, not an error. @return None."""
    assert pnp.register(np.zeros((0, 2)), np.zeros((0, 2)))["matched"] == 0


X3_TEXT = """%TF.FileFunction,Component,L1,Top*%
%FSLAX46Y46*%
%MOMM*%
%LPD*%
G01*
%TA.AperFunction,ComponentMain*%
%ADD10C,0.300000*%
%TD*%
%TA.AperFunction,ComponentOutline,Courtyard*%
%ADD11C,0.100000*%
%TD*%
%TA.AperFunction,ComponentPin*%
%ADD12P,0.360000X4X0.000000*%
%TD*%
D10*
%TO.C,D4*%
%TO.CFtp,1006_C*%
%TO.CVal,TVS*%
%TO.CMnt,SMD*%
%TO.CRot,-90*%
X150400000Y-96750000D03*
D11*
X150125000Y-96000000D02*
X150675000Y-96000000D01*
X150675000Y-97500000D01*
X150125000Y-97500000D01*
X150125000Y-96000000D01*
D12*
%TO.P,D4,1,A1*%
X150400000Y-96300000D03*
%TO.P,D4,2,A2*%
X150400000Y-97200000D03*
%TD*%
M02*
"""


def test_x3_components(tmp_path):
    """!@brief A part of an X3 component layer keeps its reference, footprint, rotation, origin, courtyard and pins. @param tmp_path pytest folder. @return None."""
    f = tmp_path / "comp.gbr"
    f.write_text(X3_TEXT)
    parts = x3.components(f)
    assert len(parts) == 1
    p = parts[0]
    assert p["ref"] == "D4" and p["footprint"] == "1006_C" and p["value"] == "TVS" and p["rotation"] == -90.0
    assert p["origin"] == pytest.approx((150.4, -96.75))
    assert len(p["courtyard"]) == 5 and len(p["pins"]) == 2
    assert x3.courtyard_box(p) == pytest.approx((150.125, -97.5, 150.675, -96.0))
