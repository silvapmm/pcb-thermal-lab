#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_conformance.py
@brief Conformance of pcbthermal.gerber with the research reader (research/gerber-import/lib/native_gerber.py) on the real boards of research/gerber-real-boards.
@details The real boards are third-party files kept out of git (`data/` is ignored), so every test here skips when the research reader or the boards are absent. The folders searched
         are the environment variable PCBT_GERBER_DATA, the repository's own research/gerber-real-boards/data and the data folder of the research worktree of the maintainer. The
         program's reader must agree with the prototype it was ported from: the copper area of every layer within 3 % (it agrees within 0.05 % in the run recorded in the report), the
         holes of every drill file (count, positions and plating), the X2 layer functions, and closed outlines whose boxes match the research stroke boxes. The Ucamco layer-format test
         files that the research could read are rasterised too, and the two it refuses (aperture blocks) are refused here.
"""

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from pcbthermal import gerber as G
from pcbthermal.gerber.excellon import is_gerber_text

REPO = Path(__file__).resolve().parents[1]
RESEARCH_READER = REPO / "research" / "gerber-import" / "lib" / "native_gerber.py"
CANDIDATES = [os.environ.get("PCBT_GERBER_DATA", ""), str(REPO / "research" / "gerber-real-boards" / "data"),
              "/Volumes/SSD/PROJETOS/pcb-thermal-lab/.claude/worktrees/agent-aa828a7a970c19021/research/gerber-real-boards/data",
              "/Volumes/SSD/PROJETOS/pcb-thermal-lab/research/gerber-real-boards/data"]
PIX = 0.1
BOARDS = ["rp2040", "stickhub", "vstcm", "oswlight", "isastm"]


def _data_dir():
    """!
    @brief The first folder of real boards that exists.
    @return Path or None.
    """
    for c in CANDIDATES:
        if c and (Path(c) / "rp2040").is_dir():
            return Path(c)
    return None


def _research_reader():
    """!
    @brief Import the research reader by file path under a private module name (the tests never put the research folder on sys.path).
    @return The module, or None when the file is absent.
    """
    if not RESEARCH_READER.exists():
        return None
    spec = importlib.util.spec_from_file_location("research_native_gerber", RESEARCH_READER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DATA = _data_dir()
NG = _research_reader()
needs_boards = pytest.mark.skipif(DATA is None or NG is None, reason="the research reader or the git-ignored real boards are not available")


@needs_boards
@pytest.mark.parametrize("board", BOARDS)
def test_copper_area_agrees_with_the_research_reader(board):
    files = sorted(p for p in (DATA / board).glob("*.gbr") if p.name[0] in "FBL" and p.name[1:].split(".")[0] in ("", "2", "3"))
    assert files
    for f in files:
        layer = G.read_layer(f)
        win = G.window_of(layer.bbox())
        rows, cols = G.pixel_counts(win, PIX)
        win = G.Window(win.x_left, win.y_top, cols * PIX, rows * PIX)               # a whole number of pixels, as the research window is
        cov = G.rasterize(layer, win, PIX, 4)
        ref = NG.render_coverage(NG.Layer(f.read_text(errors="replace")), win.x_left, win.y_top, win.width, win.height, PIX, 4)
        ours, theirs = G.coverage_area_mm2(cov, PIX), float(ref.sum()) * PIX * PIX
        assert ours == pytest.approx(theirs, rel=0.03), f.name
        assert ours == pytest.approx(theirs, rel=1e-3), f.name                         # in practice the same algorithm: the tolerance of the brief is far looser
        assert cov.shape == ref.shape and np.abs(cov / 255.0 - ref).mean() < 1e-3


@needs_boards
@pytest.mark.parametrize("board", BOARDS)
def test_drill_files_agree_with_the_research_reader(board):
    f = DATA / board / "drill.drl"
    ours = G.read_drill_file(f)
    if is_gerber_text(f.read_text(errors="replace")):
        # StickHub writes its drill layer as X2 Gerber: the research reader (Excellon only) returns 86 holes of diameter 0 in micrometres; ours reads the flashes
        layer = G.read_layer(f)
        assert len(ours.holes) == len(layer.flashes()) == 87 and ours.plated is True and ours.span == (1, 2)
        assert {round(h.diameter, 3) for h in ours.holes} == {0.3, 0.4}
        return
    theirs = NG.read_drill(f)
    assert len(ours.holes) == len(theirs) and len(theirs) > 0
    for h, (x, y, d, plated) in zip(ours.holes, theirs):
        if not h.is_slot:
            assert (h.x, h.y) == (pytest.approx(x), pytest.approx(y))
        else:                                                                           # the research keeps the middle of the slot only
            assert ((h.x + h.x_end) / 2, (h.y + h.y_end) / 2) == (pytest.approx(x), pytest.approx(y))
        assert h.diameter == pytest.approx(d) and h.plated == plated


@needs_boards
@pytest.mark.parametrize("board", BOARDS)
def test_outline_is_closed_and_its_box_matches_the_research_stroke_box(board):
    f = DATA / board / "edge.gbr"
    out = G.read_outline(f.read_text(errors="replace"), f.name)
    assert out.area_mm2 > 100 and len(out.polygons) >= 1
    x0, y0, x1, y1 = NG.layer_bbox(f)                                                   # includes the half width of the strokes
    bx0, by0, bx1, by1 = out.bbox
    half = max(ap.radius for ap in G.read_layer(f).apertures.values())
    assert (bx0 - x0, by0 - y0, x1 - bx1, y1 - by1) == pytest.approx((half,) * 4, abs=0.02)
    # The area of the polygon is the board: inside its box, and larger than the sum of the holes
    assert out.area_mm2 <= (bx1 - bx0) * (by1 - by0) + 1e-6


@needs_boards
@pytest.mark.parametrize("board", BOARDS)
def test_layer_functions_agree_with_the_research_classifier(board):
    for f in (DATA / board).glob("*.gbr"):
        theirs = NG.classify(f)
        ours = G.detect_file(f)
        if theirs[0] == "copper":
            assert ours.kind == "copper" and (theirs[1] is None or ours.side == {"top": "top", "bot": "bottom", "inr": "inner", "bottom": "bottom"}.get(theirs[1], theirs[1])), f.name
        elif theirs[0] == "outline":
            assert ours.kind == "outline", f.name
        elif theirs[0] is None:
            assert ours.kind != "copper", f.name


@needs_boards
def test_paste_layers_keep_the_component_reference_apart_from_the_net():
    # The research rewrote TO.C into the net; a paste file carries only TO.C, a copper file may carry both
    paste = G.read_layer(DATA / "isastm" / "pasteF.gbr")
    refs = paste.references()
    assert refs and paste.net_names() == []
    assert all(f.ref for f in paste.flashes() if f.ref is not None)
    copper = G.read_layer(DATA / "isastm" / "F.gbr")
    assert copper.net_names()                                                           # the copper file names its nets


@needs_boards
def test_ucamco_layer_format_files_and_the_refused_aperture_blocks():
    folder = DATA / "ucamco" / "layer_format_tests"
    if not folder.is_dir():
        pytest.skip("the Ucamco layer-format test files are not in the data folder")
    refused = []
    for f in sorted(folder.glob("*.gbr")):
        text = f.read_text(errors="replace")
        try:
            layer = G.parse_layer(text, f.name)
        except G.UnsupportedFeatureError as exc:
            refused.append(f.name)
            assert exc.file == f.name
            continue
        bb = layer.bbox()
        if bb is None:
            continue
        win = G.window_of(bb)
        pix = max(win.width, win.height) / 400.0
        cov = G.rasterize(layer, win, pix, 2)
        assert cov.sum() > 0, f.name
        try:
            ref = NG.Layer(text)
        except NotImplementedError:
            continue
        refcov = NG.render_coverage(ref, win.x_left, win.y_top, cov.shape[1] * pix, cov.shape[0] * pix, pix, 2)
        assert G.coverage_area_mm2(cov, pix) == pytest.approx(float(refcov.sum()) * pix * pix, rel=0.03), f.name
    assert set(refused) <= {"Block_with_different_orientations.gbr", "Nested_blocks.gbr"} and refused
