#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_placement_preamble.py
@brief Tests of the placement reader with a free-text preamble before the header row (the Pulsonix position file) and of the import messages about it.
@details The tables are invented in the layout of the Pulsonix file (title, date, `Units,mm`, a row of commas, then `Ref,Part Name,Side,X,Y,Rotation`); no third-party file is in the
         repository. The real file is read only when `PCBT_GERBER_SAMPLES` (or `PCBT_REAL_BOARDS`) holds it. Conventions accepted: unit from a `Units,<mm|mil|in>` line (default mm), side
         words Top/Bottom, rotation in degrees counter-clockwise, Y up as in the other formats.
         Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_placement_preamble.py`.
"""

import os
import random
import time
from pathlib import Path

import pytest

from pcbthermal.gerber import parts as P

PULSONIX = ("my board - COMPONENT PLACEMENT,\n1/2/2020,\nUnits,mm,\n,\nRef,Part Name,Side,X,Y,Rotation,\n"
            "X1,ABS05,Top,-2.50,-4.00,0.0,\nU2,ATSAMD21E,Bottom,0.00,0.00,0.0,\nC2,C 0.1uF 0201,Top,5.25,1.75,180.0,\n")


def test_pulsonix_style_preamble_is_skipped():
    """!
    @brief The title, date, units and separator rows above the header are skipped and the rows are read.
    @return None
    """
    info = {}
    rows = P.parse_placement(PULSONIX, "pos.csv", info)
    assert [r["ref"] for r in rows] == ["X1", "U2", "C2"]
    assert (rows[0]["x"], rows[0]["y"], rows[2]["rot"]) == (-2.5, -4.0, 180.0)
    assert rows[1]["side"] == "bottom" and rows[0]["package"] == ""
    # three lines of text (the row of commas is not text), header on line 5, millimetres
    assert info == {"preamble_lines": 3, "header_line": 5, "unit": "mm"}


def test_units_line_of_the_preamble_sets_the_unit():
    """!
    @brief `Units,mil` and `Units,in` in the preamble scale the values; a header unit still wins.
    @return None
    """
    (r,) = P.parse_placement("Title,\nUnits,mil,\nRef,X,Y\nR1,1000,2000\n")
    assert r["x"] == pytest.approx(25.4) and r["y"] == pytest.approx(50.8)
    (r,) = P.parse_placement("Title\nUnits,in,\nRef,X,Y\nR1,1,2\n")
    assert r["x"] == pytest.approx(25.4)
    (r,) = P.parse_placement("Units,mil,\nRef,X (mm),Y (mm)\nR1,1,2\n")
    assert r["x"] == 1.0


def test_previous_formats_are_unchanged_and_report_no_preamble():
    """!
    @brief A file with the header on the first line, and a KiCad report, give the same rows and `preamble_lines` 0.
    @return None
    """
    info = {}
    (a,) = P.parse_placement("Ref,Val,Package,PosX,PosY,Rot,Side\nR1,10k,R_0402,1,2,90,top\n", info=info)
    assert (a["x"], a["y"], a["rot"]) == (1.0, 2.0, 90.0) and info["preamble_lines"] == 0 and info["header_line"] == 1
    kicad = "### Module positions - created on x ###\n## Unit = mm, Angle = deg.\n## Side : All\n# Ref     Val   Package   PosX  PosY  Rot  Side\nR1 10k R_0402 1.0 2.0 90 top\n"
    info = {}
    (k,) = P.parse_placement(kicad, info=info)
    assert k["x"] == 1.0 and info["preamble_lines"] == 0


def test_no_header_is_refused_in_plain_words():
    """!
    @brief Text without a header row, in any length, is refused with a message that says no header was found (never "empty"), within a bounded number of lines.
    @return None
    """
    with pytest.raises(ValueError, match="no placement header found"):
        P.parse_placement("title\nfoo,bar\n1,2\n", "p.csv")
    long = "\n".join(f"line {i},text" for i in range(5000)) + "\nRef,X,Y\nR1,1,2\n"
    with pytest.raises(ValueError, match=f"first {P.MAX_PREAMBLE_LINES} lines"):
        P.parse_placement(long, "p.csv")
    with pytest.raises(ValueError, match="empty"):
        P.parse_placement(" \n\n")


def test_header_just_inside_the_limit_is_found():
    """!
    @brief A preamble of exactly the limit of text lines still finds the header, one more does not.
    @return None
    """
    n = P.MAX_PREAMBLE_LINES
    text = "\n".join(f"note {i}" for i in range(n)) + "\nRef,X,Y\nR1,1,2\n"
    info = {}
    assert P.parse_placement(text, info=info)[0]["ref"] == "R1" and info["preamble_lines"] == n and info["header_line"] == n + 1
    with pytest.raises(ValueError, match="no placement header found"):
        P.parse_placement("\n".join(f"note {i}" for i in range(n + 1)) + "\nRef,X,Y\nR1,1,2\n")


def test_hostile_preambles_stay_linear_and_safe():
    """!
    @brief Very long lines, NUL and binary bytes, many separators and every preamble length neither crash (only ValueError) nor take long.
    @return None
    """
    rng = random.Random(7)
    t0 = time.perf_counter()
    hostile = ["x" * 5_000_000, "," * 2_000_000, ";" * 300_000, "\x00\x00,\x00", '"' * 200_000, "\t" * 500_000, "".join(chr(rng.randrange(256)) for _ in range(5000))]
    for h in hostile:
        # as a preamble line before a valid table (long ones are skipped unparsed) and alone (no header: a ValueError)
        try:
            rows = P.parse_placement(f"{h}\nRef,X,Y\nR1,1,2\n", "h.csv")
            assert rows and rows[0]["ref"] == "R1"
        except ValueError:
            pass
        with pytest.raises(ValueError):
            P.parse_placement(h, "h.csv")
    for n in range(0, 80):
        text = "\n".join(f"free text {i}, with commas; and (brackets)" for i in range(n)) + "\nRef,Part Name,Side,X,Y,Rotation,\nR1,a,Top,1,2,0,\n"
        try:
            info = {}
            assert P.parse_placement(text, info=info)[0]["ref"] == "R1"
            assert info["preamble_lines"] == n and n <= P.MAX_PREAMBLE_LINES
        except ValueError as exc:
            assert n > P.MAX_PREAMBLE_LINES and "first" in str(exc)
    assert time.perf_counter() - t0 < 10.0


def test_session_notes_the_skipped_lines_and_matches_by_position_only_when_read(tmp_path):
    """!
    @brief Through `ImportSession`: a preamble file gives a plain note; a refused placement file produces no "matched by position" sentence and says why.
    @param tmp_path Scratch folder.
    @return None
    """
    from pcbthermal.gui.import_session import ImportSession, PLACEMENT
    (tmp_path / "pos.csv").write_text(PULSONIX, encoding="utf-8")
    s = ImportSession()
    s.set_files([str(tmp_path / "pos.csv")])
    f = next(x for x in s.files if x.name == "pos.csv")
    f.role, f.use = PLACEMENT, True
    s.build_parts()
    assert not f.error
    assert any("line 5" in w and "3 lines of text" in w for w in s.parts_warnings())
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "bad.csv").write_text("nothing,useful\n1,2\n", encoding="utf-8")
    s2 = ImportSession()
    s2.set_files([str(tmp_path / "bad" / "bad.csv")])
    g = next(x for x in s2.files if x.name == "bad.csv")
    g.role, g.use = PLACEMENT, True
    s2.build_parts()
    assert "no placement header found" in g.error
    assert not any("matched to the placement file by position" in w for w in s2.parts_warnings())


def _real_file():
    """!
    @brief The Pulsonix position file of the local library, when the environment holds it.
    @return Path or None.
    """
    for var in ("PCBT_GERBER_SAMPLES", "PCBT_REAL_BOARDS"):
        base = os.environ.get(var, "")
        if base and Path(base).is_dir():
            for root, _, names in os.walk(base, followlinks=True):     # the library folders are symlink farms
                for nm in names:
                    if "Component Positions" in nm and nm.endswith(".csv"):
                        return Path(root) / nm
    return None


@pytest.mark.skipif(_real_file() is None, reason="the Pulsonix sample is not in PCBT_GERBER_SAMPLES / PCBT_REAL_BOARDS")
def test_real_pulsonix_position_file_reads():
    """!
    @brief The real Pulsonix position file (local library, not in the repository) reads: 86 rows, header on line 5, millimetres.
    @return None
    """
    info = {}
    p = _real_file()
    rows = P.parse_placement(p.read_text(encoding="utf-8", errors="replace"), p.name, info)
    assert len(rows) == 86 and info["header_line"] == 5 and info["unit"] == "mm" and info["preamble_lines"] == 3
