#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_imported_copper.py
@brief Tests of the imported copper (`pcbthermal/copper.py`): simple boards with known answers first (uniform copper, stripes, a window, a ring, a one-dimensional chain),
       then the order of the face construction (the unreduced sheet counts the laminate twice), the five models, the project round trip and the memory terms, and last real
       windows of downloaded boards against the program's own network on the pixel (the error of the mapping alone) and against the independent 3D solver.
@details The reference of the mapping is the program's network with the same laminate rule on the pixel grid (one cell per pixel, fill 0 or 1): the difference between a variant and
         it is the error of the mapping alone (research/gerber-real-boards README 10.5). The real boards are not in the repository (git-ignored data of
         research/gerber-real-boards); their tests are skipped when the files are absent. Every test is meant to run in under 20 s.
"""

import copy
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from pcbthermal import api, copper, fdm, fvm, gerber, memory
from pcbthermal.model import ImportRecord, ImportedCopper, Problem
from pcbthermal.project import Project, load_project, save_project

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "gerber-real-boards" / "lib"))     # ref3d.py: the independent 3D solver (imports nothing from pcbthermal)
sys.path.insert(0, str(ROOT / "tests" / "helpers"))

import gerber_text as gt  # noqa: E402

PIX = 0.1               # mm, the pixel of the windows
WINDOW = 12.0           # mm
THICK = 1.6             # mm
H_FACE = 10.0           # W/m2K on both faces, adiabatic sides (the setting of README 10)


# ---------------------------------------------------------------------------------------------------- helpers
def _stripes(n, pitch=9, width=4):
    """!
    @brief A coverage raster of vertical copper stripes.
    @param n Pixels per side.
    @param pitch Stripe pitch in pixels.
    @param width Stripe width in pixels.
    @return uint8 array (n, n).
    """
    a = np.zeros((n, n), np.uint8)
    for j in range(0, n, pitch):
        a[:, j:j + width] = 255
    return a


def _solid(n):
    """!
    @brief A full-copper raster.
    @param n Pixels per side.
    @return uint8 array (n, n).
    """
    return np.full((n, n), 255, np.uint8)


def _board(rasters, mapping, side=WINDOW, heater=4.8, pix=PIX, power=1.0, kind="coverage"):
    """!
    @brief A square board of imported copper (every layer a raster) with one square heater at the centre of the top layer.
    @param rasters List of uint8 rasters, top first.
    @param mapping Copper mapping.
    @param side Board side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @param power Heat in W.
    @param kind Mask kind to pack.
    @return Problem.
    """
    p = Problem.new(side, side, layers=len(rasters), thickness_mm=THICK, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    c = side / 2
    p.add_heater(1, power, rect=(c - heater / 2, c - heater / 2, c + heater / 2, c + heater / 2))
    p.imported = copper.imported_from_rasters(rasters, pix, mapping, kind=kind)
    return p


def _heater_mean(theta, cell, side=WINDOW, heater=4.8):
    """!
    @brief Mean rise of the top layer over the cells whose centres lie in the heater block.
    @param theta Array (layers, ny, nx), rows from the bottom.
    @param cell Cell in mm.
    @param side Board side in mm.
    @param heater Heater side in mm.
    @return float K.
    """
    c = side / 2
    x = (np.arange(theta.shape[2]) + 0.5) * cell
    y = (np.arange(theta.shape[1]) + 0.5) * cell
    m = (x[None, :] > c - heater / 2) & (x[None, :] < c + heater / 2) & (y[:, None] > c - heater / 2) & (y[:, None] < c + heater / 2)
    return float(theta[0][m].mean())


def _solve(p, cell, faces=None, side=WINDOW, heater=4.8):
    """!
    @brief The heater mean of the FVM at a cell.
    @param p Problem.
    @param cell Cell in mm.
    @param faces Argument `faces` of the network (None: the problem's own).
    @param side Board side in mm.
    @param heater Heater side in mm.
    @return float K.
    """
    n = int(round(side / cell))
    th, _ = fvm.Network(p, n, n, faces=faces).solve_steady()
    return _heater_mean(th, cell, side, heater)


def _pixel_reference(rasters, side=WINDOW, heater=4.8, pix=PIX):
    """!
    @brief The program's own network on the pixel grid (fill 0 or 1, the laminate rule on): the limit that a mapping on the program's network can reach.
    @param rasters List of uint8 rasters, top first.
    @param side Board side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @return float K, the heater mean.
    """
    return _solve(_board(rasters, "fill", side, heater, pix), pix, side=side, heater=heater)


def _pct(a, b):
    """!
    @brief Percent difference.
    @param a Value.
    @param b Reference.
    @return float 100 (a / b - 1).
    """
    return 100.0 * (a / b - 1.0)


# ---------------------------------------------------------------------------------------------------- packed masks and the record
@pytest.mark.parametrize("kind", ["coverage", "binary"])
def test_pack_unpack_round_trip(kind):
    """!
    @brief A packed mask unpacks to the same bytes (a binary mask to 0 and 255) and survives the JSON text.
    @param kind Mask kind.
    @return None.
    """
    rng = np.random.default_rng(3)
    a = (rng.random((37, 53)) * 255).astype(np.uint8) if kind == "coverage" else (rng.random((37, 53)) > 0.5)
    m = json.loads(json.dumps(copper.pack_coverage(a, kind)))
    b = copper.unpack_coverage(m)
    assert b.dtype == np.uint8 and b.shape == a.shape
    assert np.array_equal(b, a if kind == "coverage" else a * np.uint8(255))
    with pytest.raises(ValueError):
        copper.pack_coverage(a, "nonsense")


def test_resample_conserves_area_and_aligned_is_exact():
    """!
    @brief Averaging a raster onto the board grid keeps the copper area, and a whole number of pixels per cell is the plain block mean.
    @return None.
    """
    rng = np.random.default_rng(5)
    a = (rng.random((60, 60)) * 255).astype(np.uint8)
    pix = 0.2e-3
    c = copper.resample_coverage(a, pix, 12e-3, 12e-3, 10, 10)                    # 6 pixels per cell, aligned
    blocks = a.astype(float).reshape(10, 6, 10, 6).mean(axis=(1, 3))[::-1] / 255.0
    assert np.allclose(c, blocks, atol=1e-6)
    d = copper.resample_coverage(a, pix, 12e-3, 12e-3, 7, 9)                      # not aligned
    assert abs(d.mean() - a.mean() / 255.0) < 1e-5                                # (equal cells: the mean of the cells is the mean of the pixels)


def test_copy_of_a_problem_shares_the_packed_masks_and_is_cheap():
    """!
    @brief The masks stay packed text, so a deep copy (an undo snapshot) shares the strings and costs next to nothing, whatever the pixels.
    @return None.
    """
    rasters = [_stripes(2000, 40, 11), _solid(2000), _stripes(2000, 25, 7), _solid(2000)]       # 4 layers of 4 million pixels
    p = _board(rasters, "faces", side=200.0, heater=10.0, pix=0.1)
    t0 = time.perf_counter()
    q = copy.deepcopy(p)
    dt = time.perf_counter() - t0
    assert q.imported.layers[0]["mask"]["data"] is p.imported.layers[0]["mask"]["data"]
    assert dt < 0.05
    assert sum(len(e["mask"]["data"]) for e in p.imported.layers) < 200_000        # a few KB of text for 16 million pixels
    first = copper.unpack_coverage(p.imported.layers[0]["mask"])
    assert copper.unpack_coverage(q.imported.layers[0]["mask"]) is first            # the arrays are made once for all the copies


def test_undo_snapshot_of_a_project_with_masks_is_cheap():
    """!
    @brief The undo snapshot of the document (project_to_dict and a deep copy) of a project with four 4-million-pixel masks shares the packed text and costs milliseconds.
    @return None.
    """
    from pcbthermal.project import project_to_dict
    rasters = [_stripes(2000, 40, 11), _solid(2000), _stripes(2000, 25, 7), _solid(2000)]
    p = _board(rasters, "faces", side=200.0, heater=10.0, pix=0.1)
    proj = Project(problem=p, imports=[ImportRecord(name="big", box_mm=[0, 0, 200, 200], copper=p.imported)])
    t0 = time.perf_counter()
    snap = copy.deepcopy(project_to_dict(proj))
    dt = time.perf_counter() - t0
    assert dt < 0.1
    assert snap["imports"][0]["copper"]["layers"][0]["mask"]["data"] is proj.imports[0].copper.layers[0]["mask"]["data"]


def test_project_round_trip_with_masks(tmp_path):
    """!
    @brief A project with an imported board saves as format 2 with its masks, loads back with the same copper, and gives the same temperatures.
    @param tmp_path pytest folder.
    @return None.
    """
    p = _board([_stripes(120), _solid(120)], "faces")
    rec = ImportRecord(name="stripes", box_mm=[0, 0, 12, 12], copper=p.imported)
    path = tmp_path / "board.pcbt.json"
    save_project(path, Project(problem=p, imports=[rec]))
    d = json.loads(path.read_text())
    assert d["format"].endswith("-2") and "mapping" not in d["imports"][0]["copper"]      # the default mapping is not written
    back = load_project(path)
    c = back.imports[0].copper
    assert c.layers == p.imported.layers and c.pix_mm == p.imported.pix_mm and c.mapping == "faces"
    assert d["project"].get("imported") is None and "imported" not in json.dumps(d["project"])      # the problem JSON carries no masks; the record does
    q = back.problem
    assert q.imported is c and abs(_solve(q, 0.6) - _solve(p, 0.6)) < 1e-12           # loading hands the masks of the record to the problem
    assert Project(problem=p).run_problem() is p                                      # no record: the problem itself
    p.imported.mapping = "lambda"
    assert ImportedCopper.from_dict(p.imported.to_dict()).mapping == "lambda"
    # A record written before the mapping field existed reads as the default
    old = {k: v for k, v in p.imported.to_dict().items() if k != "mapping"}
    assert ImportedCopper.from_dict(old).mapping == "faces"


# ---------------------------------------------------------------------------------------------------- simple boards with known answers
def test_uniform_copper_is_the_zone_path():
    """!
    @brief Full copper on both layers through the masks gives the same temperatures as two zones of fill 1, whatever the mapping.
    @return None.
    """
    n = int(WINDOW / PIX)
    z = Problem.new(WINDOW, WINDOW, layers=2, thickness_mm=THICK, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    z.add_heater(1, 1.0, rect=(3.6, 3.6, 8.4, 8.4))
    z.add_zone(1, rect=(0, 0, WINDOW, WINDOW), fill=1.0)
    z.add_zone(2, rect=(0, 0, WINDOW, WINDOW), fill=1.0)
    ref, _ = fvm.Network(z, 20, 20).solve_steady()
    for mapping in copper.MAPPINGS:
        p = _board([_solid(n), _solid(n)], mapping)
        th, _ = fvm.Network(p, 20, 20).solve_steady()
        assert np.abs(th - ref).max() < 1e-6, mapping                                  # (the pixel sheet is float32: 1e-9 of the rise)


def test_stripes_face_conductances_are_the_closed_forms():
    """!
    @brief For stripes the local problem has an exact answer: along the stripes the faces are the arithmetic mean of the sheet, across them the harmonic mean.
    @return None.
    """
    n = 8
    s_cu, s_lam = 0.0137, 0.0014
    row = np.where(np.arange(4 * n) % 4 < 2, s_cu, s_lam)                            # stripes along x: rows alternate copper and bare
    sheet = np.repeat(row[:, None], 4 * n, axis=1)
    gx, gy = copper.face_conductances(sheet, n, "faces")
    assert np.allclose(gx, row.reshape(4, n).mean(axis=1)[:, None] * np.ones((1, 3)), rtol=1e-10)      # parallel: arithmetic
    assert np.allclose(gy, 1.0 / np.mean(1.0 / row.reshape(4, n)[0]), rtol=1e-10)                      # in series: harmonic (every window holds whole periods)
    lx, ly = copper.face_conductances(sheet, n, "lambda")
    assert np.allclose(lx, gx, rtol=1e-10) and np.allclose(ly, gy, rtol=1e-10)         # the two Wiener bounds meet on stripes, so lambda is exact too
    with pytest.raises(ValueError):
        copper.face_conductances(sheet, 7)


def test_one_dimensional_chain_is_the_series_circuit():
    """!
    @brief Four full-copper layers heated over the whole top face: the rise is the series-parallel circuit of the films and the dielectric gaps.
    @details T = P R, with the top film in parallel with the chain of the three gaps and the bottom film (copper nodes have no resistance; the program's gap is the
             dielectric thickness over the through conductivity).
    @return None.
    """
    n = 24
    p = Problem.new(12.0, 12.0, layers=4, thickness_mm=1.6, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=(0, 0, 12, 12))
    p.imported = copper.imported_from_rasters([_solid(n)] * 4, 0.5, "faces")
    b = p.board
    area = b.width * b.height
    r_chain = float(np.sum(b.gap_thicknesses() / (b.gap_properties()[0] * area)))
    r_top, r_bot = 1.0 / (H_FACE * area), 1.0 / (H_FACE * area)
    expected = 1.0 / (1.0 / r_top + 1.0 / (r_chain + r_bot))
    th, _ = fvm.Network(p, 6, 6).solve_steady()
    assert abs(th[0].mean() / expected - 1.0) < 1e-9
    assert np.ptp(th[0]) < 1e-9 * expected                                            # one-dimensional: no lateral variation


def test_window_and_ring_symmetry_and_heat_balance():
    """!
    @brief A plane with a bare window and a ring of copper are symmetric under the mirror images of the board, so the field is; the heat leaving is the power.
    @return None.
    """
    n = int(WINDOW / PIX)
    plane = _solid(n)
    plane[40:80, 40:80] = 0                                                           # a bare window under the heater
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(yy - (n - 1) / 2, xx - (n - 1) / 2)
    ring = np.where((r > 30) & (r < 45), 255, 0).astype(np.uint8)
    for raster in (plane, ring):
        p = _board([raster, _solid(n)], "faces")
        res = fvm.solve_steady(p, cell_mm=0.6)
        t = res.T[0] - p.board.ambient
        assert np.allclose(t, t[:, ::-1], rtol=1e-8, atol=1e-8) and np.allclose(t, t[::-1, :], rtol=1e-8, atol=1e-8)
        assert abs(sum(res.power_out.values()) / 1.0 - 1.0) < 1e-9
        assert abs(res.power_in - 1.0) < 1e-12


def test_window_faces_beat_the_fill_against_the_pixel_network():
    """!
    @brief A plane with a bare window (3 to 9 mm) and a copper pad inside it, heated over the window: at a cell that cuts the window edge the faces stay within 1 % of the
           program's pixel network and the fill fraction is 12 % cool.
    @details At 0.6 mm both mappings read 0.6 % (the cells hold nearly pure copper or bare laminate, so the mappings agree); at 1.2 mm the faces read +1.75 and the fill -1.89 %.
    @return None.
    """
    n = int(WINDOW / PIX)
    top = _solid(n)
    top[30:90, 30:90] = 0
    top[50:70, 50:70] = 255
    rasters = [top, _solid(n)]
    ref = _pixel_reference(rasters)
    err = {(m, c): _pct(_solve(_board(rasters, m), c), ref) for c in (0.6, 2.4) for m in ("fill", "faces", "lambda")}
    assert abs(err["faces", 0.6]) < 1.0 and abs(err["faces", 2.4]) < 1.0
    assert err["fill", 2.4] < -8.0 and abs(err["lambda", 2.4]) < 2.0


def test_stripes_two_layers_faces_against_the_pixel_network():
    """!
    @brief Stripes over a solid bottom: the faces are within 1 % of the pixel network at the cells of README 10 (0.6 and 1.2 mm), the fill fraction is about 5 % cool.
    @return None.
    """
    n = int(WINDOW / PIX)
    rasters = [_stripes(n), _solid(n)]
    ref = _pixel_reference(rasters)
    for cell in (0.6, 1.2):
        f = _pct(_solve(_board(rasters, "faces"), cell), ref)
        d = _pct(_solve(_board(rasters, "fill"), cell), ref)
        assert abs(f) < 1.0, (cell, f)
        assert -8.0 < d < -3.5, (cell, d)


def test_naive_face_order_is_worse():
    """!
    @brief Faces built from the sheet BEFORE the laminate rule moved its part into the interior nodes count the laminate twice: they must be clearly worse.
    @details This is the test that fails if the construction is done in the naive order (INTEGRATION 1, README 10): the proper faces are within 1 % of the pixel network
             on two layers of stripes, the naive ones several times farther.
    @return None.
    """
    n = int(WINDOW / PIX)
    rasters = [_stripes(n), _solid(n)]
    ref = _pixel_reference(rasters)
    p = _board(rasters, "faces")
    good = abs(_pct(_solve(p, 0.6), ref))
    naive_src = copper.CopperSource.of(p)
    naive_src.reduce_sheet = False
    naive = abs(_pct(_solve(p, 0.6, faces=naive_src), ref))
    assert good < 1.0 and naive > 2.0 and naive > 3.0 * good, (good, naive)


def test_fdm_takes_the_faces_and_corrects_the_fill():
    """!
    @brief The FDM with imported copper agrees with the FVM on the same board and its fill mapping is as cool as the FVM's: the faces fix the same bias in both.
    @return None.
    """
    n = int(WINDOW / PIX)
    rasters = [_stripes(n), _solid(n)]
    out = {}
    for mapping in ("fill", "faces"):
        p = _board(rasters, mapping)
        r = fdm.solve_steady(p, cell_mm=0.6)
        c = 0.6
        x = np.arange(r.T.shape[2]) * c
        m = (x[None, :] > 3.6 - 1e-9) & (x[None, :] < 8.4 + 1e-9) & (x[:, None] > 3.6 - 1e-9) & (x[:, None] < 8.4 + 1e-9)
        out[mapping] = float((r.T[0] - p.board.ambient)[m].mean())
    fvm_faces = _solve(_board(rasters, "faces"), 0.6)
    assert abs(_pct(out["faces"], fvm_faces)) < 2.5
    assert _pct(out["fill"], out["faces"]) < -3.0                                     # the fill reads cool in the FDM too
    # The FDM faces are built on node-centred windows: the symmetric board gives a symmetric field
    p = _board(rasters, "faces")
    t = fdm.solve_steady(p, cell_mm=0.6).T[0]
    assert np.allclose(t, t[::-1, :], rtol=1e-8, atol=1e-8)


def test_five_models_run_and_warn():
    """!
    @brief Imported copper runs in all five models: the layered models say what the copper is, Lumped and Analytic always warn (a sample, not a bound), the 3D solid says it reads the fill.
    @return None.
    """
    n = int(WINDOW / PIX)
    p = _board([_stripes(n), _solid(n)], "faces")
    sim = api.simulate(p, api.SolverOptions(models=("fvm", "fdm", "lumped", "analytic", "solid3d"), cell_mm=1.0))
    assert set(sim.results) == {"fvm", "fdm", "lumped", "analytic", "solid3d"}
    for name in ("lumped", "analytic"):
        assert any("imported copper on the Lumped" in w for w in sim.results[name].warnings), name
    for name in ("lumped", "analytic"):
        w = [x for x in sim.results[name].warnings if "imported copper on the Lumped" in x][0]
        # The text states the cases honestly: windows and the whole board, a sample and not a bound, and who reads the copper
        assert "not a bound" in w and "24 windows" in w and "whole RP2040 board" in w and "27 to 42 %" in w and "17 to 35 %" in w and "do read it" in w, name
    assert any("imported copper in the 3D solid" in w for w in sim.results["solid3d"].warnings)
    assert any("import" in w for w in sim.results["fvm"].warnings) and any("import" in w for w in sim.results["fdm"].warnings)
    # A drawn board gets none of these
    q = Problem.new(WINDOW, WINDOW, layers=2, h_side=None)
    q.add_heater(1, 1.0, rect=(4, 4, 8, 8))
    sim2 = api.simulate(q, api.SolverOptions(models=("fvm", "lumped", "solid3d"), cell_mm=1.0))
    assert not any("import" in w for r in sim2.results.values() for w in r.warnings)
    # The 3D solid reads the cell fill: it equals the FVM with the fill mapping (so about 6 % cool on stripes against the faces), which the warning says
    fill_fvm = fvm.solve_steady(_board([_stripes(n), _solid(n)], "fill"), cell_mm=1.0).t_max
    assert abs(sim.results["solid3d"].t_max / fill_fvm - 1.0) < 0.02


def test_problem_without_imports_takes_the_old_path():
    """!
    @brief A drawn board has no copper source, and `faces=False` on an imported board gives the zone path (no copper at all).
    @return None.
    """
    q = Problem.new(WINDOW, WINDOW, layers=2, h_side=None)
    q.add_heater(1, 1.0, rect=(4, 4, 8, 8))
    q.add_zone(1, rect=(0, 0, 6, 12), fill=1.0)
    assert fvm.Network(q, 12, 12).copper is None and copper.CopperSource.of(q) is None
    p = _board([_solid(120), _solid(120)], "faces")
    assert fvm.Network(p, 12, 12, faces=False).copper is None
    assert np.allclose(fvm.Network(p, 12, 12, faces=False).fill, 0.0)


# ---------------------------------------------------------------------------------------------------- the import
def _gerber_stripes(width_mm, height_mm, pitch_mm, line_mm):
    """!
    @brief A synthetic copper layer of vertical stripes (strokes of a round aperture) and its outline, as Gerber text.
    @param width_mm Board width in mm.
    @param height_mm Board height in mm.
    @param pitch_mm Stripe pitch in mm.
    @param line_mm Stripe width in mm.
    @return Tuple (copper text, outline text).
    """
    aperture = f"%ADD10C,{line_mm}*%\n"
    body = gt.header("%TF.FileFunction,Copper,L1,Top*%\n" + aperture) + "G01*\n"
    x = line_mm / 2
    while x < width_mm:
        body += gt.line(x, 0.0, x, height_mm)
        x += pitch_mm
    body += gt.end()
    edge = gt.header("%ADD11C,0.1*%\n") + "G01*\nD11*\n"
    for (a, b, c, d) in ((0, 0, width_mm, 0), (width_mm, 0, width_mm, height_mm), (width_mm, height_mm, 0, height_mm), (0, height_mm, 0, 0)):
        edge += gt.line(a, b, c, d, 11)
    return body, edge + gt.end()


def test_import_copper_from_gerber_text():
    """!
    @brief The importer turns a Gerber layer into a packed mask with the copper area of the stripes, a Problem of the right size, and the memory guard refuses before drawing.
    @return None.
    """
    top, edge = _gerber_stripes(12.0, 12.0, 1.0, 0.4)
    layers = [gerber.parse_layer(top, "top.gtl"), gerber.parse_layer(top, "bot.gbl")]
    outline = gerber.read_outline(edge, "edge.gm1")
    ib = copper.import_copper(layers, outline, pixel_mm=0.1, cell_mm=1.0)
    assert (ib.width_mm, ib.height_mm) == pytest.approx((12.1, 12.1), abs=0.11) or ib.width_mm > 11.9
    cov = copper.unpack_coverage(ib.copper.layers[0]["mask"])
    area = float(cov.sum()) / 255.0 * ib.pixel_mm ** 2
    assert 0.35 < area / (ib.width_mm * ib.height_mm) < 0.45                           # stripes of 0.4 mm at a pitch of 1 mm, plus the edge lines
    p = ib.to_problem(thickness_mm=1.6)
    assert p.board.layers == 2 and p.imported is ib.copper and len(ib.copper.layers) == 2
    rec = ib.record("synthetic")
    assert rec.copper is ib.copper and rec.box_mm == list(ib.box_mm)
    # The default pixel gives at least ten pixels per cell, so the run's own coarse-raster warning stays silent (thin 0.127 mm tracks at cells of 0.5, 1 and 2 mm)
    thin_top, thin_edge = _gerber_stripes(6.0, 6.0, 1.0, 0.127)
    thin = [gerber.parse_layer(thin_top, "t.gtl")]
    for cell in (0.5, 1.0, 2.0):
        auto = copper.import_copper(thin, gerber.read_outline(thin_edge, "e.gm1"), cell_mm=cell)
        assert cell / auto.pixel_mm >= 10.0 - 1e-9 and auto.pixel_mm <= 0.127 + 1e-9
        assert not any("pixels per cell" in w for w in copper.model_warnings(auto.to_problem(), "fvm", cell))
    # The guard: a machine with 0.2 GB cannot draw 12 x 12 mm at 1 micrometre; the message names the pixel that fits
    with pytest.raises(memory.MemoryGuardError) as e:
        copper.import_copper(layers, outline, pixel_mm=0.001, cell_mm=1.0, ram=int(0.5e9), base=0.1e9)
    assert "pixel of" in str(e.value) and "more" in str(e.value)
    with pytest.raises(ValueError):
        copper.import_copper([])


def test_memory_terms_for_imported_copper(monkeypatch):
    """!
    @brief The guard counts the masks and the face construction: the run of an imported board is estimated higher than the same board drawn, in proportion to the pixels.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(memory, "resident_bytes", lambda: 0.108e9)
    small = _board([_solid(120), _solid(120)], "faces")
    big = _board([_solid(2000), _solid(2000)], "faces", side=200.0, pix=0.1)
    assert memory.copper_run_bytes(Problem.new(12, 12)) == 0.0
    assert memory.copper_run_bytes(big) > memory.copper_run_bytes(small) + 100e6
    drawn = Problem.new(12, 12, layers=2)
    drawn.add_heater(1, 1.0, rect=(4, 4, 8, 8))
    v0 = memory.check(drawn, ("fvm",), 1.0, refuse="return", quiet=True, base=0.108e9)[0]
    v1 = memory.check(small, ("fvm",), 1.0, refuse="return", quiet=True, base=0.108e9)[0]
    assert v1.estimate > v0.estimate
    fill = copy.deepcopy(big)
    fill.imported.mapping = "fill"
    assert memory.copper_run_bytes(fill) < memory.copper_run_bytes(big)                 # no window problems with the fill mapping
    with pytest.raises(memory.MemoryGuardError):
        memory.check_import(20000, 20000, 4, 1.0, ram=int(8e9), base=0.1e9, pixel_mm=0.01)


# ---------------------------------------------------------------------------------------------------- real boards
def _data_folders():
    """!
    @brief The folders that may hold the downloaded boards (git-ignored data of research/gerber-real-boards).
    @return List of Path.
    """
    out = []
    if os.environ.get("PCBT_REAL_BOARDS"):
        out.append(Path(os.environ["PCBT_REAL_BOARDS"]))
    out.append(ROOT / "research" / "gerber-real-boards" / "data")
    if os.environ.get("PCBT_GERBER_DATA"):
        out.append(Path(os.environ["PCBT_GERBER_DATA"]))
    out.append(ROOT / "pcb-library" / "env" / "data")                # local ignored library, see pcb-library/scripts/link_env.sh
    return out


def _board_files(key):
    """!
    @brief The copper layers (top down) of a downloaded board, or None.
    @param key Board folder name.
    @return List of Path, or None when the board is not on disk.
    """
    for d in _data_folders():
        b = d / key
        files = [b / n for n in ("F.gbr", "L2.gbr", "L3.gbr", "B.gbr") if (b / n).exists()]
        if len(files) >= 2:
            return files
    return None


BOARDS = ("rp2040", "co60", "vstcm", "isastm", "cmm2", "oswlight", "stickhub")


def _real_window(key, side=WINDOW, heater=4.8, pix=PIX):
    """!
    @brief A window of a real board whose heater block is about half copper on the top layer, rasterised at the pixel of the study (binary pixel-centre mask).
    @details Deterministic: the top copper is drawn on the whole board at 0.4 mm, windows of 12 mm are tried on a 4 mm lattice, and the one whose central block is nearest
             to 55 % copper (with 25 to 85 % in the window) is taken.
    @param key Board folder name.
    @param side Window side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @return List of uint8 rasters (rows from the top, 0 or 255), top layer first, or None when the board is absent.
    """
    files = _board_files(key)
    if files is None:
        return None
    layers = [gerber.read_layer(f) for f in files]
    x0, y0, x1, y1 = layers[0].bbox()
    coarse = gerber.rasterize(layers[0], gerber.Window(x0, y1, x1 - x0, y1 - y0), 0.4, 1) > 127
    best = None
    step = int(round(4.0 / 0.4))
    w = int(round(side / 0.4))
    h = int(round(heater / 0.4))
    for i in range(0, coarse.shape[0] - w, step):
        for j in range(0, coarse.shape[1] - w, step):
            win = coarse[i:i + w, j:j + w]
            core = win[(w - h) // 2:(w - h) // 2 + h, (w - h) // 2:(w - h) // 2 + h]
            if 0.25 < win.mean() < 0.85 and 0.3 < core.mean() < 0.8 and all(l.bbox() is not None for l in layers):
                score = abs(core.mean() - 0.55)
                if best is None or score < best[0]:
                    best = (score, i, j)
    if best is None:
        return None
    _, i, j = best
    window = gerber.Window(x0 + j * 0.4, y1 - i * 0.4, side, side)
    return [gerber.rasterize(l, window, pix, 1) for l in layers]


@pytest.fixture(scope="module")
def real_windows():
    """!
    @brief The real windows, one per board that is on disk.
    @return dict key -> list of rasters.
    """
    out = {}
    for key in BOARDS:
        w = _real_window(key)
        if w is not None:
            out[key] = w
    if len(out) < 6:
        pytest.skip(f"fewer than six downloaded boards on disk ({sorted(out)}); run research/gerber-real-boards/scripts/fetch_boards.py")
    return out


def test_real_windows_mapping_alone(real_windows, capsys):
    """!
    @brief On real windows the faces on the reduced sheet reproduce the numbers of README 10.5 (the mapping alone, against the program's pixel network): the faces carry a fraction of
           a percent, the fill fraction several times more, and the faces are closer in almost every window and cell.
    @param real_windows Fixture with the windows.
    @param capsys pytest fixture.
    @return None.
    """
    rows = []
    for key, rasters in real_windows.items():
        ref = _pixel_reference(rasters)
        for cell in (0.6, 1.2):
            f = _pct(_solve(_board(rasters, "faces"), cell), ref)
            d = _pct(_solve(_board(rasters, "fill"), cell), ref)
            rows.append((key, len(rasters), cell, f, d))
    with capsys.disabled():
        print("\nreal windows, mapping alone (percent of the heater mean rise; faces / fill):")
        for r in rows:
            print(f"  {r[0]:9s} L{r[1]} cell {r[2]}: faces {r[3]:+.2f}  fill {r[4]:+.2f}")
    faces = np.array([abs(r[3]) for r in rows])
    fill = np.array([abs(r[4]) for r in rows])
    assert faces.mean() < 1.0 and faces.max() < 3.0                                   # README 10.5: 0.2 to 0.7 % mean, worst 2.65 %
    assert 1.2 < fill.mean() < 4.0                                                    # README 10.5: 1.7 to 3.2 %
    assert (faces < fill).sum() >= len(rows) - 2                                      # README 10.5: 41 of 42


def test_real_windows_at_the_program_cells(real_windows, capsys):
    """!
    @brief The mapping alone at cells of 1 and 2 mm (10 and 20 pixels per cell, heater 4 mm with its edges on the cell lines): the faces stay within a few percent of the
           program's pixel network, the fill fraction is 3 to 9 % cool. Cells of 0.5 mm need a 0.05 mm pixel (study_program_cells.py: 0.2 to 0.3 % on four layers).
    @param real_windows Fixture with the windows.
    @param capsys pytest fixture.
    @return None.
    """
    faces, fill = [], []
    rows = []
    for key in ("isastm", "rp2040", "co60", "stickhub"):
        if key not in real_windows:
            continue
        rasters = real_windows[key]
        ref = _solve(_board(rasters, "fill", heater=4.0), PIX, heater=4.0)
        for cell in (1.0, 2.0):
            f = _pct(_solve(_board(rasters, "faces", heater=4.0), cell, heater=4.0), ref)
            d = _pct(_solve(_board(rasters, "fill", heater=4.0), cell, heater=4.0), ref)
            faces.append(abs(f))
            fill.append(abs(d))
            rows.append((key, cell, f, d))
    with capsys.disabled():
        print("\nreal windows at the program's cells (heater 4 mm; faces / fill, percent):  " + "; ".join(f"{k} {c:g} mm {f:+.2f}/{d:+.2f}" for k, c, f, d in rows))
    assert np.mean(faces) < 2.5 and max(faces) < 4.5
    assert np.mean(fill) > 3.0 and sum(a < b for a, b in zip(faces, fill)) >= len(faces) - 1      # (README 10.5: 41 of 42)


def test_real_windows_against_the_3d_reference(real_windows, capsys):
    """!
    @brief Against the independent 3D solver (README 10 setting: 12 mm windows, heater 4.8 mm, cells 0.6 and 1.2 mm, the laminate rule on): the faces reproduce the numbers of README 10.2
           (mean error 1.2 to 1.6 %, the fill fraction 3 to 5 %), and on two layers the faces built on the unreduced sheet are clearly worse.
    @param real_windows Fixture with the windows.
    @param capsys pytest fixture.
    @return None.
    """
    import ref3d
    rows = []
    for key in ("rp2040", "vstcm", "isastm"):
        if key not in real_windows:
            continue
        rasters = real_windows[key]
        L = len(rasters)
        gap = (THICK * 1e-3 - L * 35e-6) / (L - 1)
        masks = [(r > 127)[::-1] for r in rasters]
        m = ref3d.build(masks, PIX * 1e-3, 35e-6, [gap] * (L - 1), n_sub=8 if L == 2 else 3, h_top=H_FACE, h_bottom=H_FACE)
        c = WINDOW / 2
        xs = (np.arange(masks[0].shape[1]) + 0.5) * PIX
        hm = (xs[None, :] > c - 2.4) & (xs[None, :] < c + 2.4) & (xs[:, None] > c - 2.4) & (xs[:, None] < c + 2.4)
        ref = float(ref3d.solve(m, hm, 1.0)["top"][hm].mean())
        for cell in (0.6, 1.2):
            p = _board(rasters, "faces")
            src = copper.CopperSource.of(p)
            src.reduce_sheet = False
            rows.append((key, L, cell, _pct(_solve(p, cell), ref), _pct(_solve(_board(rasters, "fill"), cell), ref), _pct(_solve(p, cell, faces=src), ref)))
    with capsys.disabled():
        print("\nreal windows against the 3D reference (percent of the heater mean rise; faces / fill / naive faces):")
        for r in rows:
            print(f"  {r[0]:8s} L{r[1]} cell {r[2]}: faces {r[3]:+.2f}  fill {r[4]:+.2f}  naive {r[5]:+.2f}")
    f = np.abs([r[3] for r in rows])
    d = np.abs([r[4] for r in rows])
    assert f.mean() < 2.0 and f.max() < 3.0                                           # README 10.2: 1.2 to 1.6 % mean, 3.5 % worst
    assert d.mean() > 2.5 and (f < d).all()                                           # README 10.2: 2.8 to 4.8 %
    two = [r for r in rows if r[1] == 2]
    assert all(abs(r[5]) > abs(r[3]) + 1.0 for r in two)                              # the laminate counted twice: README 10.2, 4.2 against 3.6 % on two layers


def test_fdm_on_a_real_window(real_windows):
    """!
    @brief The FDM with imported copper agrees with the FVM on a real window within 3 % and its fill mapping is as cool as the FVM's.
    @param real_windows Fixture with the windows.
    @return None.
    """
    rasters = real_windows["isastm"]
    out = {}
    for mapping in ("faces", "fill"):
        p = _board(rasters, mapping)
        r = fdm.solve_steady(p, cell_mm=0.6)
        x = np.arange(r.T.shape[2]) * 0.6
        m = (x[None, :] > 3.6 - 1e-9) & (x[None, :] < 8.4 + 1e-9) & (x[:, None] > 3.6 - 1e-9) & (x[:, None] < 8.4 + 1e-9)
        out[mapping] = float((r.T[0] - p.board.ambient)[m].mean())
    ref = _solve(_board(rasters, "faces"), 0.6)
    assert abs(_pct(out["faces"], ref)) < 3.0
    assert out["fill"] < out["faces"]


def test_faces_are_the_research_prototype():
    """!
    @brief The faces of the program equal the flow-based faces and the lambda faces of the research prototype (research/gerber-models/lib/conduction.py) on random sheets, to 1e-10.
    @return None.
    """
    lib = ROOT / "research" / "gerber-models" / "lib"
    if not (lib / "conduction.py").exists():
        pytest.skip("the research prototype is not in this tree")
    sys.path.insert(0, str(lib))
    try:
        import conduction as cd
    finally:
        sys.path.remove(str(lib))
    rng = np.random.default_rng(1)
    for ny, nx, n in ((5, 7, 6), (9, 4, 10), (3, 12, 4)):
        s = np.where(rng.random((ny * n, nx * n)) > 0.5, 0.0137, 0.0014)
        gx, gy = cd.dual_faces(s, n, 0)
        hx, hy = copper.face_conductances(s, n, "faces")
        assert np.allclose(gx, hx, rtol=1e-10, atol=0) and np.allclose(gy, hy, rtol=1e-10, atol=0)
        lx, ly = cd.faces_from_cells(*cd.map_lambda(cd.cell_blocks(s, n), 0.5))
        mx, my = copper.face_conductances(s, n, "lambda")
        assert np.allclose(lx, mx, rtol=1e-10, atol=0) and np.allclose(ly, my, rtol=1e-10, atol=0)


def test_warning_for_a_raster_too_coarse_for_the_cell():
    """!
    @brief Fewer than eight pixels per cell cannot resolve the copper in the face problems: the run says so (0.1 mm pixel, 0.5 mm cell), and says nothing at ten.
    @return None.
    """
    p = _board([_stripes(120), _solid(120)], "faces")
    assert any("pixels per cell" in w for w in copper.model_warnings(p, "fvm", 0.5))
    assert not any("pixels per cell" in w for w in copper.model_warnings(p, "fvm", 1.0))
    assert not any("pixels per cell" in w for w in copper.model_warnings(p, "lumped", 0.5))


def test_coarse_cell_warnings_and_their_thresholds():
    """!
    @brief The coarse-cell warning starts above 1 mm (not at 1 mm), the screening wording above 1.5 mm, the numbers are the measured ones, and the 'fill' mapping has neither.
    @return None.
    """
    p = _board([_stripes(120), _solid(120)], "faces", pix=0.1)
    texts = lambda cell: copper.model_warnings(p, "fvm", cell)                # noqa: E731
    assert not any("above 1 mm" in w for w in texts(1.0))
    assert any("above 1 mm" in w for w in texts(1.2))
    assert not any("screening" in w for w in texts(1.2))
    assert not any("screening" in w for w in texts(1.5))
    assert any("screening" in w for w in texts(2.0))
    w = [w for w in texts(2.0) if "above 1 mm" in w][0]
    assert "7 to 10 %" in w and "up to 4.3 %" in w and "about half" not in w
    assert "+2.2 %" in w and "+11.8 %" in w and "bare laminate" in w            # Grid error with drawn full copper and on bare laminate (validation 27.3)
    assert not any("above 1 mm" in w for w in copper.model_warnings(_board([_stripes(120), _solid(120)], "fill", pix=0.1), "fvm", 2.0))


def test_the_grid_error_quoted_for_drawn_full_copper():
    """!
    @brief The coarse-cell warning quotes +2.2 % at 2 mm as the program's grid error with drawn FULL copper (24 mm board, 4 mm part, h = 10, 2 layers, against 0.25 mm);
           the first text of the reopened branch quoted +11.8 % for it, which is the number of the same board with no copper at all.
    @return None.
    """
    from pcbthermal import fvm

    def heater_mean(p, cell):
        n = int(round(24.0 / cell))
        theta = fvm.Network(p, n, n).solve_steady()[0]
        x = (np.arange(n) + 0.5) * cell
        inside = (x > 10.0) & (x < 14.0)
        return float(theta[0][inside[:, None] & inside[None, :]].mean())

    p = Problem.new(24.0, 24.0, layers=2, thickness_mm=1.6, copper_um=35, h_top=10.0, h_bottom=10.0, h_side=None).add_heater(1, 1.0, rect=(10, 10, 14, 14))
    for layer in (1, 2):
        p.add_zone(layer, rect=(0.0, 0.0, 24.0, 24.0))
    err = 100.0 * (heater_mean(p, 2.0) / heater_mean(p, 0.25) - 1.0)
    assert 2.1 < err < 2.25, err                                                   # Measured +2.17 % (study_grid_error_drawn_copper.py)


def test_auto_cell_is_capped_at_one_millimetre_with_imported_copper():
    """!
    @brief Auto (suggest_cell_mm) never proposes more than 1 mm for imported copper when the memory allows, where the same board drawn would get the cell of its part (3 mm here, capped at 2 mm),
           and says so (auto_cell_note) when the memory forces a larger cell.
    @return None.
    """
    from pcbthermal import suggest_cell_mm

    p = _board([_solid(240), _solid(240)], "faces", side=24.0, heater=12.0, pix=0.1)
    plain = Problem.new(24.0, 24.0, layers=2).add_heater(1, 1.0, rect=(6, 6, 18, 18))
    assert suggest_cell_mm(plain) == pytest.approx(2.0)
    assert suggest_cell_mm(p) == pytest.approx(1.0)
    assert suggest_cell_mm(p, models=("fvm",)) == pytest.approx(1.0)
    assert suggest_cell_mm(Problem.new(24.0, 24.0, layers=2)) == 2.0                  # no copper import, no part: unchanged
    assert suggest_cell_mm(_board([_solid(240), _solid(240)], "fill", side=24.0, heater=12.0, pix=0.1)) == pytest.approx(2.0)
    assert copper.auto_cell_note(p, 1.0) == "" and copper.auto_cell_note(plain, 3.0) == ""
    assert "screening" in copper.auto_cell_note(p, 2.0) and "memory" in copper.auto_cell_note(p, 1.25)
    assert "screening" not in copper.auto_cell_note(p, 1.25)



def test_auto_note_is_shown_by_the_command_line_and_the_auto_button(monkeypatch, capsys):
    """!
    @brief When the memory forces Auto above 1 mm on imported copper, `--cell-mm auto` prints copper.auto_cell_note and the Auto button of the Simulation panel shows it
           (the review found the note defined but shown nowhere).
    @return None.
    """
    import argparse

    from pcbthermal import cli

    p = _board([_solid(240), _solid(240)], "faces", side=24.0, heater=12.0, pix=0.1)
    monkeypatch.setattr(cli, "suggest_cell_mm", lambda *a, **k: 2.0)               # As if the memory limit had enlarged the cell to 2 mm
    assert cli._cell_arg(argparse.Namespace(cell_mm="auto", model="fvm"), p, 1.0) == 2.0
    assert "screening estimate" in capsys.readouterr().err
    plain = Problem.new(24.0, 24.0, layers=2).add_heater(1, 1.0, rect=(6, 6, 18, 18))
    cli._cell_arg(argparse.Namespace(cell_mm="auto", model="fvm"), plain, 1.0)
    assert capsys.readouterr().err == ""                                           # No imported copper: no note


def test_auto_button_shows_the_imported_copper_note(qtbot, monkeypatch):
    """!
    @brief The Auto button of the Simulation panel shows copper.auto_cell_note when the memory pushes an imported board above 1 mm.
    @param qtbot pytest-qt fixture.
    @param monkeypatch pytest fixture.
    @return None.
    """
    pytest.importorskip("pytestqt")
    from pcbthermal.gui import panels
    from pcbthermal.gui.document import Document

    doc = Document()
    doc.open_problem(_board([_solid(240), _solid(240)], "faces", side=24.0, heater=12.0, pix=0.1))
    panel = panels.SolverPanel(doc)
    qtbot.addWidget(panel)
    monkeypatch.setattr(panels, "suggest_cell_mm", lambda problem, models=None, **k: 1.25 if models is not None else 1.0)
    panel._auto_cell()
    assert "imported copper" in panel.status.text() and "memory limit" in panel.status.text()

# ---------------------------------------------------------------------------------------------------- review: hostile records, misaligned cells, saving, live checks
def _checker(n, square=6):
    """!
    @brief A checker of copper squares that touch only at their corners (the pattern a partial pixel at a corner bridges).
    @param n Pixels per side.
    @param square Side of a square in pixels.
    @return uint8 array (n, n).
    """
    yy, xx = np.mgrid[0:n, 0:n]
    return np.where(((xx // square) + (yy // square)) % 2 == 0, 255, 0).astype(np.uint8)


def test_damaged_masks_are_refused_without_filling_the_memory():
    """!
    @brief A project file is hostile input: a zip bomb (a small text that inflates to 200 MB for a mask of 10 x 10 pixels), damaged text, a binary mask whose bytes
           do not fit its shape, and absurd shapes are refused with a ValueError, and the bomb is never inflated beyond the bytes the shape needs.
    @return None.
    """
    import base64
    import tracemalloc
    import zlib
    bomb = {"kind": "coverage", "shape": [10, 10], "data": base64.b64encode(zlib.compress(bytes(200_000_000), 9)).decode()}
    copper.clear_cache()
    tracemalloc.start()
    with pytest.raises(ValueError):
        copper.unpack_coverage(bomb)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert peak < 20e6                                                                # (the uncapped inflate took 449 MB here)
    good = copper.pack_coverage(_stripes(40) > 127, "binary")
    for bad in ({**good, "shape": [400, 400]},                                        # bits for 1600 pixels declared as 160 000 (padded with zeros before the review)
                {**good, "data": "!!!not base64"}, {**good, "data": base64.b64encode(b"garbage").decode()},
                {**good, "shape": [-5, 10]}, {**good, "shape": [10]}, {**good, "shape": [10 ** 6, 10 ** 6]}, {**good, "kind": "rle"}, {"data": good["data"]}):
        with pytest.raises(ValueError):
            copper.unpack_coverage(bad)


def test_masks_that_do_not_cover_the_board_are_refused_and_said_live():
    """!
    @brief Masks whose extent is not the board box (a board resized after the import, a damaged pixel) are refused by the models, and the live check says why instead of
           failing; an infinite pixel is refused. A board scaled by the equivalent rectangle keeps its masks valid.
    @return None.
    """
    from pcbthermal.checks import check_problem
    p = _board([_solid(120), _solid(120)], "faces")
    p.board.width *= 1.05                                                             # 12 mm masks on a 12.6 mm board
    with pytest.raises(ValueError, match="resized"):
        fvm.Network(p, 12, 12)
    warns = check_problem(p, 1.0)
    assert any("imported copper cannot be used" in w for w in warns)
    q = _board([_solid(120), _solid(120)], "faces")
    q.imported.pix_mm = float("inf")
    with pytest.raises(ValueError):
        copper.CopperSource.of(q)
    r = _board([_solid(120), _solid(120)], "faces")
    t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    r.board.outline = np.c_[6 + 6 * np.cos(t), 6 + 6 * np.sin(t)] / 1000.0
    e, s = r.equivalent_rectangle()
    assert s < 1.0 and copper.CopperSource.of(e) is not None


def test_faces_at_a_cell_that_is_not_a_whole_number_of_pixels():
    """!
    @brief A cell is almost never a whole number of raster pixels; averaging the mask onto the grid of the face problems made partial pixels that bridged the corners of a
           checker (16 to 17 % cool against the pixel network at cells of 0.923 and 1.333 mm before the review). Sampling keeps the error at the level of the aligned cells.
    @return None.
    """
    n = int(WINDOW / PIX)
    ref = _pixel_reference([_checker(n), _solid(n)])
    for m in (13, 9):
        cell = WINDOW / m
        p = _board([_checker(n), _solid(n)], "faces")
        th, _ = fvm.Network(p, m, m).solve_steady()
        assert abs(_pct(_heater_mean(th, cell), ref)) < 6.0, m
    src = copper.CopperSource.of(_board([_checker(n), _solid(n)], "faces"))
    assert src.pixels_per_cell(0.5e-3, 0.5e-3) == 6                                   # five pixels per cell round up (Python's round(2.5) gave 4)


def test_saving_a_problem_with_copper_and_no_record_keeps_the_copper(tmp_path):
    """!
    @brief A problem from ImportedBoard.to_problem saved without an import record used to lose its masks (the native problem JSON has no place for them); it is saved as
           format 2 with a record of its own and reopens with the same copper.
    @param tmp_path pytest folder.
    @return None.
    """
    p = _board([_stripes(120), _solid(120)], "faces")
    path = tmp_path / "bare.pcbt.json"
    save_project(path, Project(problem=p))
    back = load_project(path)
    assert back.problem.imported is not None and back.problem.imported.layers == p.imported.layers
    assert abs(_solve(back.problem, 1.0) - _solve(p, 1.0)) < 1e-12


def test_a_zone_on_an_imported_layer_is_said_to_be_ignored():
    """!
    @brief The masks replace the zones of an imported layer, so a zone drawn there is ignored by every model: the live check says so, and nothing is said for a zone on a layer
           that is not imported.
    @return None.
    """
    from pcbthermal.checks import check_problem
    p = Problem.new(WINDOW, WINDOW, layers=2, thickness_mm=THICK, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=(4, 4, 8, 8))
    p.imported = copper.imported_from_rasters([_stripes(120)], PIX, "faces")          # only the top layer is imported
    p.add_zone(1, rect=(0, 0, 6, 6), fill=1.0, name="top plane")
    p.add_zone(2, rect=(0, 0, 6, 6), fill=1.0, name="bottom plane")
    warns = check_problem(p, 1.0)
    assert any("top plane" in w and "ignored" in w for w in warns)
    assert not any("bottom plane" in w and "ignored" in w for w in warns)


def test_no_copper_edge_warning_on_an_imported_layer_even_for_lumped():
    """!
    @brief The "copper edge or hatching crosses its footprint" warning is not produced for a part on an imported-copper layer, whatever model is
           requested (imported copper has its own, stronger warning).
    @return None.
    """
    from pcbthermal.checks import check_input
    n = int(WINDOW / PIX)
    p = _board([_stripes(n), _solid(n)], "faces")
    for models in (("lumped",), ("analytic",), ("fvm", "lumped", "analytic")):
        assert not [w for w in check_input(p, models, 1.0) if "copper edge" in str(w)], models
