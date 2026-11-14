#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_drawn_copper_faces.py
@brief Drawn copper (zones, hatching) read as imported copper in the FVM and FDM: the exact cell fill and the flow-based faces of the layers that have a cell cut by a zone edge.
@details The references are the heater-mean rises of an independent hexahedral finite-element solution of the three 20 mm boards of `research/drawn-copper-faces` (extrapolated to
         zero size, 200 W/m2K, two layers; README 2.1 there), stored here as numbers. Before the change the FVM read the inset square -1.2 / -2.8 % (1 / 0.5 mm), the stripes board
         -8.0 / -4.1 % and the L -1.4 / -4.1 %; now +0.1 / -1.4, -0.6 / -1.9 and -0.0 / -2.5 %. Also: the exact area of the raster, the union of zones, the layers that keep the
         earlier path (bit for bit), the Lumped, Analytic and 3D solid untouched, the heat balance, and the memory law above the measured peaks. The three boards are also
         boards of the release harness (`regress_boards.py`); the harness freezes them at the next release (a board absent from the frozen file cannot be a pending record), so their
         numbers at 1 and 0.5 mm are held here until then.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "regression"))
import regress_boards as B                                                  # noqa: E402
from pcbthermal import Problem, api, copper, fdm, fvm, memory       # noqa: E402

# Heater-mean rise (K) of the finite-element solution, extrapolated to zero size (research/drawn-copper-faces README 2.1)
FEM = {"drawn_inset_square": 57.157, "drawn_stripes_pad": 73.872, "drawn_ell": 64.563}
# What the branch gives (K), frozen: model, cell in mm
FROZEN = {
    "drawn_inset_square": {("fvm", 1.0): 57.216642, ("fvm", 0.5): 56.375651, ("fdm", 1.0): 56.609878, ("fdm", 0.5): 56.495192},
    "drawn_stripes_pad": {("fvm", 1.0): 73.465223, ("fvm", 0.5): 72.477498, ("fdm", 1.0): 72.540350, ("fdm", 0.5): 72.467266},
    "drawn_ell": {("fvm", 1.0): 64.558501, ("fvm", 0.5): 62.978721, ("fdm", 1.0): 61.978150, ("fdm", 0.5): 62.573500},
}


def heater_mean(p, model, cell):
    """!
    @brief Mean rise of the heater footprint (the network's own weights) of a steady FVM or FDM solution.
    @param p Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return Mean rise in K.
    """
    if model == "fvm":
        nx = max(int(round(p.board.width * 1e3 / cell)), 2)
        net = fvm.Network(p, nx, nx, assemble=False)
        r = fvm.solve_steady(p, cell_mm=cell)
    else:
        net = fdm.Network(p, cell)
        r = fdm.solve_steady(p, cell_mm=cell)
    assert abs(r.balance_error) < 1e-9
    t = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: t.size]
    return float((w * (t - r.ambient)).sum() / w.sum())


@pytest.mark.parametrize("name,fvm_1mm,fvm_05mm", [("drawn_inset_square", 0.6, 1.9), ("drawn_stripes_pad", 1.0, 2.4), ("drawn_ell", 0.6, 3.0)])
def test_fvm_error_against_the_finite_elements(name, fvm_1mm, fvm_05mm):
    """!
    @brief The FVM heater mean is within the stated error of the finite elements (the earlier path read -1.2, -8.0 and -1.4 % at 1 mm: all three fail the first bound).
    @param name Board of the harness.
    @param fvm_1mm Largest absolute error at 1 mm, %.
    @param fvm_05mm Largest absolute error at 0.5 mm, % (what is left is the laminate rule).
    @return None.
    """
    p = B.build(name)
    for cell, bound in ((1.0, fvm_1mm), (0.5, fvm_05mm)):
        err = 100.0 * (heater_mean(p, "fvm", cell) / FEM[name] - 1.0)
        assert abs(err) < bound, f"{name} {cell} mm: {err:+.2f} %"


def test_fdm_error_against_the_finite_elements():
    """!
    @brief The FDM stripes board read -12.9 % at 1 mm before; now within 2.5 %, and the inset square within 1.5 %.
    @return None.
    """
    for name, bound in (("drawn_stripes_pad", 2.5), ("drawn_inset_square", 1.5)):
        err = 100.0 * (heater_mean(B.build(name), "fdm", 1.0) / FEM[name] - 1.0)
        assert abs(err) < bound, f"{name}: {err:+.2f} %"


@pytest.mark.parametrize("name", sorted(FROZEN))
def test_frozen_numbers_of_the_harness_boards(name):
    """!
    @brief The three new harness boards at 1 and 0.5 mm in the FVM and FDM keep the numbers of this change (1e-6 K) until the harness freezes them.
    @param name Board.
    @return None.
    """
    p = B.build(name)
    for (model, cell), want in FROZEN[name].items():
        assert abs(heater_mean(p, model, cell) - want) < 1e-6, (name, model, cell)


def test_raster_area_is_exact_also_for_an_edge_that_cuts_pixels():
    """!
    @brief The float raster has exactly the area of the zone; the 4 x 4 samples of the older rule do not.
    @return None.
    """
    p = B.build("drawn_inset_square")
    src = copper.drawn_source(p, 20, 20)
    r = src.raster(0)
    pix = src.pix * 1e3
    assert abs(r.sum() / 255.0 * pix * pix - 17.6 * 17.6) < 1e-3
    q = Problem.new(20, 20, 2)
    q.add_zone(1, polygon=[[1.13, 1.13], [18.77, 1.13], [18.77, 18.77], [1.13, 18.77]])
    r2 = copper.drawn_source(q, 20, 20).raster(0)
    assert abs(r2.sum() / 255.0 * pix * pix - 17.64 ** 2) < 1e-3


def test_cell_fill_is_the_exact_area_share():
    """!
    @brief A cell the edge cuts has the exact share, not a multiple of 1/16, and the network reads it.
    @return None.
    """
    q = Problem.new(20, 20, 2)
    q.add_zone(1, polygon=[[1.13, 1.13], [18.77, 1.13], [18.77, 18.77], [1.13, 18.77]])
    fill = copper.drawn_layer_cuts(q, 20, 20)[0]
    assert fill[0, 0] == 0.0 and abs(fill[1, 1] - 0.87 * 0.87) < 1e-6 and abs(fill[1, 5] - 0.87) < 1e-6      # the copper starts 1.13 mm in: corner cell (1, 1) and edge cell
    net = fvm.Network(q, 20, 20, assemble=False)
    assert abs(net.fill[0, 1, 1] - 0.87 * 0.87) < 1e-6


def test_union_of_zones_touching_overlapping_and_hatched():
    """!
    @brief Two zones that meet inside a cell add; an overlap is not counted twice; a hatch zone under a solid one keeps the larger fill; a hatch fill stays exact (0.7, not 178/255).
    @return None.
    """
    q = Problem.new(10, 10, 1)
    q.add_zone(1, polygon=[[0, 0], [5.5, 0], [5.5, 10], [0, 10]])
    q.add_zone(1, polygon=[[5.5, 0], [10, 0], [10, 10], [5.5, 10]])
    q.add_zone(1, polygon=[[3.2, 3.2], [7.7, 3.2], [7.7, 7.7], [3.2, 7.7]], fill=0.7)
    share, fill = copper._zone_union(q.zones, 10, 10, 1e-3, 1e-3)
    assert np.allclose(share, 1.0, atol=1e-6)                                  # the two halves meet in the column x = 5..6 and fill it
    assert np.allclose(fill[4, 4], 1.0, atol=1e-6)                             # the solid zones win over the hatch inside them
    h = Problem.new(10, 10, 1)
    h.add_zone(1, polygon=[[1.25, 1.25], [8.75, 1.25], [8.75, 8.75], [1.25, 8.75]], fill=0.7)
    src = copper.drawn_source(h, 10, 10)
    assert abs(src.raster(0).max() - 0.7 * 255.0) < 1e-3


def test_layers_without_a_cut_cell_keep_the_earlier_path_bit_for_bit():
    """!
    @brief Copper on cell lines, everywhere, hatched over the whole board or imported: no source is built and the temperatures equal those of the earlier path.
    @return None.
    """
    p = B.build("drawn_inset_square")
    assert copper.drawn_source(p, 25, 25) is not None                          # 0.8 mm cells: the edge at 1.2 mm cuts them
    q = B.build("drawn_inset_square")
    for z in q.zones:                                                          # copper to the wall on both layers: every cell full
        z.polygon = np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]) * 1e-3
    assert copper.drawn_source(q, 20, 20) is None
    assert fvm.Network(q, 20, 20).copper is None and fdm.Network(q, 1.0).copper is None
    aligned = Problem.new(20, 20, 2)                                           # an edge on a cell line (1.5 mm, cells of 0.5 mm): no cut cell
    aligned.add_zone(1, polygon=[[1.5, 1.5], [18.5, 1.5], [18.5, 18.5], [1.5, 18.5]])
    assert copper.drawn_source(aligned, 40, 40) is None
    for name in ("hatched_copper", "plate_pad"):
        assert fvm.Network(B.build(name), 30, 30, assemble=False).copper is None
    # imported copper wins: the same zones next to a mask are not rasterised again
    r = np.full((20, 20), 255, dtype=np.uint8)
    imp = Problem.new(20, 20, 2)
    imp.add_zone(1, polygon=[[1.13, 1.13], [18.77, 1.13], [18.77, 18.77], [1.13, 18.77]])
    imp.imported = copper.imported_from_rasters([r], 1.0)
    assert copper.drawn_source(imp, 20, 20) is None


def test_the_hook_is_off_for_the_lumped_network_and_the_other_models(monkeypatch):
    """!
    @brief The network the Lumped builds (no ladder, no cut cells) never reads the drawn source, and the Lumped, the Analytic and the 3D solid give the same numbers with the hook
           switched off: the review of the study found that a hook inside `fvm.Network` moved a Lumped record.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = B.build("drawn_stripes_pad")
    assert fvm.Network(p, 20, 20, assemble=False, ladder=False, cut_cells=False).copper is None
    assert fvm.Network(p, 20, 20, assemble=False).copper is not None
    runs = {}
    for tag in ("on", "off"):
        if tag == "off":
            monkeypatch.setattr(copper, "drawn_source", lambda *a, **k: None)
            monkeypatch.setattr(copper, "drawn_layer_cuts", lambda *a, **k: {})
        runs[tag] = [api.simulate(B.build(name), api.SolverOptions(models=("lumped", "analytic", "solid3d"), cell_mm=1.0))
                     for name in ("drawn_stripes_pad", "drawn_ell", "example_cut_to_T")]
    for a, b in zip(runs["on"], runs["off"]):
        for m in ("lumped", "analytic", "solid3d"):
            if m in a.results:
                assert np.array_equal(a.results[m].T, b.results[m].T), m


def test_the_fvm_equals_the_same_copper_imported():
    """!
    @brief The drawn board and a deep copy whose zones are replaced by the same exact rasters as an import (uint8) agree within the byte quantisation, and conserve the heat.
    @return None.
    """
    import copy
    p = B.build("drawn_stripes_pad")
    src = copper.drawn_source(p, 20, 20)
    q = copy.deepcopy(p)
    q.zones = []
    layers = sorted(src.layers)
    q.imported = copper.imported_from_rasters([np.round(src.raster(l)).astype(np.uint8) for l in layers], src.pix * 1e3, "faces", indices=layers)
    assert abs(heater_mean(p, "fvm", 1.0) - heater_mean(q, "fvm", 1.0)) < 5e-3


def test_drawn_layer_with_a_self_crossing_zone_keeps_the_earlier_path():
    """!
    @brief A zone that crosses itself has no exact area under the rule: the source is not built (the warning of the checks stays the user's information).
    @return None.
    """
    q = Problem.new(20, 20, 2)
    q.add_zone(1, polygon=[[1.13, 1.13], [18.77, 18.77], [18.77, 1.13], [1.13, 18.77]])
    assert copper.drawn_source(q, 20, 20) is None


def test_memory_law_covers_the_drawn_raster():
    """!
    @brief The drawn raster term is zero without a cut cell and, on a 200 x 150 mm board with stripes at 0.5 mm, at least the growth of the peak measured in the FDM (1014 MB).
    @return None.
    """
    assert memory.drawn_run_bytes(B.build("plate_pad"), 2.0) == 0.0
    big = Problem.new(200, 150, 2, h_top=10, h_bottom=10, h_side=200)
    y = 1.2
    while y < 150 - 1.2 - 1e-9:
        big.add_zone(1, rect=(1.2, y, 198.8, min(y + 1.2, 148.8)))
        y += 2.4
    big.add_zone(2, rect=(1.2, 1.2, 198.8, 148.8))
    assert memory.drawn_run_bytes(big, 0.5) >= 1014e6
    assert memory.drawn_run_bytes(big, 0.5) < 2e9                                  # a term, not the whole law
    assert memory.drawn_run_bytes(big, 0.5) > memory.drawn_run_bytes(big, 1.0) * 3.5


CHILD = """
import json, resource, sys
sys.path.insert(0, {root!r})
from pcbthermal import Problem, fvm, fdm, memory
model, cell = sys.argv[1], float(sys.argv[2])
w, h = 100, 75
p = Problem.new(w, h, 4, h_top=10, h_bottom=10, h_side=200)
for l in range(1, 5):
    p.add_zone(l, rect=(1.2, 1.2, w - 1.2, h - 1.2))
p.add_heater(1, 2.0, rect=(w / 2 - 2, h / 2 - 2, w / 2 + 2, h / 2 + 2), name="U")
base = memory.baseline_bytes()
est = memory.check(p, (model,), cell, base=base, refuse="return")[0].estimate
(fvm if model == "fvm" else fdm).solve_steady(p, cell_mm=cell)
unit = 1 if sys.platform == "darwin" else 1024
print(json.dumps({{"est": est, "peak": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit}}))
"""


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_memory_estimate_is_above_the_measured_peak(model):
    """!
    @brief A 100 x 75 mm four-layer board with copper 1.2 mm inside the wall at 0.5 mm, in a fresh process: the estimate is above the peak (measured ratios 1.4 to 1.7 on the boards of
           the review: 100 x 75 four layers, 200 x 150 with stripes, FVM and FDM).
    @param model "fvm" or "fdm".
    @return None.
    """
    out = subprocess.run([sys.executable, "-c", CHILD.format(root=str(HERE.parent)), model, "0.5"], capture_output=True, text=True, timeout=300, check=True)
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["est"] > 1.1 * r["peak"], r


def test_cells_that_are_not_square_read_the_exact_fill_on_ten_pixels():
    """!
    @brief A 20 x 20.4 mm board at 1 mm has cells of 1 x 1.02 mm: the raster is built on the grid itself (10 x 10 pixels per cell), so the cell fill is the exact area share and
           the face problems use the 10 pixels that the memory law counts (the square-pixel raster of the import gave 12 pixels per cell, sampled, and a fill off by 0.017).
    @return None.
    """
    from pcbthermal.geometry import exact_coverage
    w, h = 20.0, 20.4
    p = Problem.new(w, h, layers=2, h_top=10, h_bottom=10, h_side=200)
    p.add_zone(1, polygon=[[1.23, 1.37], [w - 1.41, 2.1], [w - 2.2, h - 1.33], [3.1, h - 2.7]])
    p.add_zone(2, rect=(1.2, 1.2, w - 1.2, h - 1.2))
    p.add_heater(1, 1.0, rect=(8, 8, 12, 12))
    nx, ny = 20, 20
    src = copper.drawn_source(p, nx, ny)
    dx, dy = p.board.width / nx, p.board.height / ny
    assert src.pixels_per_cell(dx, dy) == copper.DRAWN_PIXELS_PER_CELL
    exact = exact_coverage(np.asarray(p.zones[0].polygon), nx, ny, dx, dy)
    assert np.abs(src.fill(0, ny, nx, p.board.width, p.board.height) - exact).max() < 1e-6
    net = fvm.Network(p, nx, ny, assemble=False)
    assert np.abs(net.fill[0] - exact).max() < 1e-6
    r = fvm.solve_steady(p, cell_mm=1.0)
    assert abs(r.balance_error) < 1e-9
    assert abs(fdm.solve_steady(p, cell_mm=1.0).balance_error) < 1e-9


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_the_cell_that_fits_is_not_refused_again(model):
    """!
    @brief The cell that the refusal proposes counts the drawn raster too: checked again at that cell the run is not refused (without the raster term in the search, 50 of the 68
           limits tried here proposed a cell of 0.4 mm that `check` then refused, 1668 MB against 1650 MB).
    @param model "fvm" or "fdm".
    @return None.
    """
    w, h = 100, 75
    p = Problem.new(w, h, 4, h_top=10, h_bottom=10, h_side=200)
    for layer in range(1, 5):
        p.add_zone(layer, rect=(1.2, 1.2, w - 1.2, h - 1.2))
    p.add_heater(1, 2.0, rect=(48, 35, 52, 39))
    for ram_mb in range(600, 2000, 100):
        v = memory.check(p, (model,), 0.25, fraction=1.0, ram=int(ram_mb * 1e6), base=80e6, refuse="return", quiet=True)[0]
        if v.verdict == "refuse" and v.cell_fit:
            again = memory.check(p, (model,), v.cell_fit, fraction=1.0, ram=int(ram_mb * 1e6), base=80e6, refuse="return", quiet=True)[0]
            assert again.verdict != "refuse", (ram_mb, v.cell_fit, again.estimate)
