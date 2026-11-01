#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_component_figures.py
@brief Tests of the part-matching figures: the counts of the envelope rule on the RP2040 board, the drawing functions run, and every figure of the folder is linked (research/check_figures.py).
@details Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/gerber-real-boards/tests/test_component_figures.py`. The board tests are skipped without data/rp2040 (git-ignored; scripts/fetch_boards.py).
"""

import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data" / "rp2040"
needs_data = pytest.mark.skipif(not (DATA / "pos.csv").exists(), reason="data/rp2040 not downloaded")


@needs_data
def test_counts_of_the_two_rules():
    """!
    @brief The prototype rule matches 18 of the 30 parts, the envelope rule finds 27 (the other three are through-hole), and every opening is assigned.
    @return None
    """
    import component_match as cm
    rows, unclaimed, ctx = cm.part_rows("rp2040")
    assert len(rows) == 30
    assert sum(r["proto"] == "matched" for r in rows) == 18
    assert sum(r["improved"] for r in rows) == 27
    assert len(ctx["bypad"]) == len(ctx["pads"]) == 129
    assert len(unclaimed) == 18


@needs_data
def test_counts_against_to_c_truth():
    """!
    @brief On the boards whose paste file carries TO.C, the openings assigned by the envelope rule agree with the attribute as in README 4.9.
    @return None
    """
    import component_match as cm
    data = HERE / "data"
    if not (data / "cmm2" / "pasteF.gbr").exists():
        pytest.skip("data/cmm2 not downloaded")
    c = cm.board_counts("cmm2")
    assert (c["ok"], c["wrong"], c["missed"]) == (453, 9, 32)


@needs_data
def test_drawing_functions_write_pngs(tmp_path):
    """!
    @brief The overview, crop and source-shape drawings run and write a non-empty PNG.
    @param tmp_path pytest temporary folder.
    @return None
    """
    import component_views as cv
    cv.setup("rp2040")
    cv.draw_overviews(tmp_path / "a.png", tmp_path / "b.png")
    cv.draw_crops(tmp_path / "c.png")
    rows = cv.draw_source_shape(tmp_path / "d.png")
    assert len(rows) == 4
    assert all((tmp_path / n).stat().st_size > 10_000 for n in ("a.png", "b.png", "c.png", "d.png"))


def test_every_figure_is_linked():
    """!
    @brief research/check_figures.py passes for this folder (every PNG linked, captioned, numbers unique).
    @return None
    """
    r = subprocess.run([sys.executable, str(HERE.parent / "check_figures.py"), "gerber-real-boards"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
