#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fine_memory_format_odb.py
@brief Tests of the fine-copper detector, the memory fit, the project-file format and the ODB++ component reader, on synthetic data (no download, no program run).
"""

import json

import numpy as np
import pytest

import fine_copper as fc
import memory_model as mm
import odb
import project_format as pf
import rare_features as rf

PIX = 0.1


def stripes(width_px, pitch_px, n=200):
    """!
    @brief A mask of vertical stripes.
    @param width_px Stripe width in pixels.
    @param pitch_px Pitch in pixels.
    @param n Side of the mask in pixels.
    @return Float array (n, n).
    """
    m = np.zeros((n, n))
    for x in range(0, n, pitch_px):
        m[:, x:x + width_px] = 1.0
    return m


def test_solid_copper_is_not_fine():
    """!@brief A solid block with a clear edge has no thin copper and almost no partial cells. @return None."""
    m = np.zeros((200, 200))
    m[40:160, 40:160] = 1.0
    ind = fc.indicators(m, PIX, 1.0)
    assert ind["thin_share"] < 0.02
    assert ind["partial_share"] < 0.05


def test_fine_stripes_are_flagged():
    """!@brief Stripes 0.2 mm wide at 0.4 mm pitch are all thinner than a 1 mm cell and all in partial cells. @return None."""
    ind = fc.indicators(stripes(2, 4), PIX, 1.0)
    assert ind["thin_share"] > 0.9
    assert ind["partial_share"] > 0.9


def test_wide_stripes_are_not_thin_for_a_fine_cell():
    """!@brief Stripes 0.4 mm wide are thin for a 1 mm cell and not for a 0.2 mm cell. @return None."""
    assert fc.indicators(stripes(4, 8), PIX, 0.2)["thin_share"] < 0.1
    assert fc.indicators(stripes(4, 8), PIX, 1.0)["thin_share"] > 0.9


def test_cell_must_be_whole_pixels():
    """!@brief A cell that is not a whole number of pixels is refused. @return None."""
    with pytest.raises(ValueError):
        fc.cell_fractions(np.zeros((10, 10)), 0.1, 0.25)


def test_calibrate_threshold():
    """!@brief The threshold catches the share of bad cases asked for and reports the false alarms. @return None."""
    x = np.linspace(0, 1, 101)
    err = np.where(x > 0.5, 0.2, 0.01)
    c = fc.calibrate(x, err, err_limit=0.05, recall=0.9)
    assert 0.5 < c["threshold"] < 0.6
    assert c["recall"] >= 0.89
    assert c["false_alarm"] == 0.0
    assert np.isnan(fc.calibrate(x, np.zeros_like(x))["threshold"])


def test_fit_bytes_per_unknown():
    """!@brief Runs generated with 7 KB per unknown plus a baseline give back 7 KB. @return None."""
    u = np.array([1e5, 4e5, 1e6])
    peak = 5e8 + 7000.0 * u
    fit = mm.fit_bytes_per_unknown(u, peak, 5e8)
    assert fit["bytes_per_unknown"] == pytest.approx(7000.0)
    assert fit["max_relative_deviation"] < 1e-9
    with pytest.raises(ValueError):
        mm.fit_bytes_per_unknown([], [])
    assert mm.guard_estimate_gb(1e6, 7000.0, 0.5) == pytest.approx(7.5)
    assert mm.peak_rss_bytes() > 1e6


def test_mask_round_trip_and_size():
    """!@brief Binary masks come back exactly through JSON, coverage within 1/255, and a sparse mask packs small. @return None."""
    rng = np.random.default_rng(0)
    b = rng.random((50, 70)) > 0.5
    d = json.loads(json.dumps(pf.pack_mask(b, "binary")))
    assert np.array_equal(pf.unpack_mask(d), b)
    c = rng.random((30, 40))
    back = pf.unpack_mask(json.loads(json.dumps(pf.pack_mask(c, "coverage"))))
    assert np.max(np.abs(back - c)) <= 1.0 / 255 + 1e-12
    empty = np.zeros((1000, 1000), bool)
    assert len(json.dumps(pf.pack_mask(empty, "binary"))) < 2000
    with pytest.raises(ValueError):
        pf.pack_mask(b, "grey")


def test_migration_round_trip():
    """!@brief Format 1 goes to 2 and back unchanged; a project with imports cannot go back; an unknown format is refused. @return None."""
    d1 = {"format": pf.FORMAT_1, "board": {"w": 1}, "zones": [], "solver": {}, "view": {}}
    d2 = pf.migrate_1_to_2(d1)
    assert d2["format"] == pf.FORMAT_2 and d2["imports"] == []
    assert pf.downgrade_2_to_1(d2) == d1
    assert d1["format"] == pf.FORMAT_1                       # the argument was not changed
    d2["imports"].append(pf.import_record("b", 0.1, (0, 0, 1, 1), [("F", "top", np.ones((4, 4), bool))]))
    with pytest.raises(ValueError):
        pf.downgrade_2_to_1(d2)
    with pytest.raises(ValueError):
        pf.migrate_1_to_2({"format": "pcbthermal-project-9"})
    assert pf.migrate_1_to_2({"board": {}})["format"] == pf.FORMAT_2        # a plain native file has no format key


def test_import_record_without_embedding():
    """!@brief A reference-only record has the roles but no mask. @return None."""
    r = pf.import_record("b", 0.1, (0, 0, 1, 1), [("F", "top", np.ones((4, 4), bool))], embed=False)
    assert r["layers"][0] == {"name": "F", "role": "top"}


COMPONENTS = """UNITS=MM
# 0
CMP 0 10.5 20.25 90 N C1 100nF;0=1
PRP PART_NUMBER '100nF'
TOP 0 10.0 20.25 90 N 3 0 1
TOP 1 11.0 20.25 90 N 4 0 2
CMP 1 30.0 40.0 0 M U1 STM32;0=1
TOP 0 29.0 40.0 0 M 5 0 1
"""


def test_odb_components_parse():
    """!@brief The assumed CMP/TOP layout is parsed: two parts, pins counted, side, unit. This tests the reader against the layout written from memory; the real samples are checked by study_odb_structure.py. @return None."""
    c = odb.parse_text(COMPONENTS)
    assert [x["ref"] for x in c] == ["C1", "U1"]
    assert c[0]["pins"] == 2 and c[1]["pins"] == 1
    assert c[0]["unit"] == "mm" and c[0]["rot"] == 90.0 and c[1]["mirror"] is True
    assert odb.parse_text(COMPONENTS, "bottom")[0]["side"] == "bottom"


def test_rare_feature_counts():
    """!@brief The scanner counts aperture transformations, blocks and attributes. @return None."""
    text = "%LMX*%\n%LR45*%\n%LS0.5*%\n%ABD12*%\n%TO.C,R1*%\nG36*\n%SRX2Y1I1.0J1.0*%\n%TF.FileFunction,Copper,L1,Top*%\n"
    c = rf.count(text)
    assert c["LM (aperture mirroring)"] == 1 and c["LR (aperture rotation)"] == 1 and c["LS (aperture scaling)"] == 1
    assert c["AB (aperture block)"] == 1 and c["X3 component attribute (TO.C)"] == 1 and c["region (G36)"] == 1
    assert c["SR (step and repeat)"] == 1 and c["X2 file attribute (TF)"] == 1
    s = rf.summarise({"a": c, "b": rf.count("")})
    assert s["AB (aperture block)"][0] == 1
