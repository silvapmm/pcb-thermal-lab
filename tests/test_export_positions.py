#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_export_positions.py
@brief The positions in field_<model>.csv and surface_<model>.csv: a node field (the FDM) is written at its grid points (0 to the board size, no sample outside the board), a
       cell field (FVM, 3D solid) at the cell centres as always; the temperatures, the row count and the header do not change; the reader of columns by name still works.
"""

import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board


def read_dicts(path):
    """!
    @brief Read a CSV file by column name (what a script written for the old files does).
    @param path File path.
    @return List of dictionaries, one per row.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def odd_board():
    """!
    @brief The example board with a size that is not a whole number of 2 mm cells.
    @return Problem of 93.7 x 71.3 mm.
    """
    p = example_board()
    p.board.width, p.board.height = 0.0937, 0.0713
    return p


@pytest.fixture(scope="module", params=["example", "odd"])
def case(request, tmp_path_factory):
    """!
    @brief Run the FVM, the FDM and the 3D solid on a board and save every file.
    @param request pytest request (the board name).
    @param tmp_path_factory pytest factory of temporary directories.
    @return Tuple (simulation, output directory).
    """
    prob = example_board() if request.param == "example" else odd_board()
    sim = simulate(prob, SolverOptions(models=("fvm", "fdm", "solid3d"), cell_mm=2.0))
    d = tmp_path_factory.mktemp("export")
    sim.save(str(d), plots=False, surface_files=True)
    return sim, d


def test_fdm_field_positions_are_the_grid_points(case):
    sim, d = case
    r = sim.results["fdm"]
    rows = read_dicts(d / "field_fdm.csv")
    ny, nx = r.T.shape[1:]
    assert len(rows) == r.T.size
    xs = np.array(sorted({float(row["x_mm"]) for row in rows}))
    ys = np.array(sorted({float(row["y_mm"]) for row in rows}))
    # Grid points: from 0 to the board size, in steps of the node spacing (the last node is on the board edge, never beyond it)
    assert xs[0] == 0.0 and ys[0] == 0.0
    assert xs[-1] == pytest.approx(sim.problem.board.width * 1000, abs=1e-3)
    assert ys[-1] == pytest.approx(sim.problem.board.height * 1000, abs=1e-3)
    assert xs[-1] <= sim.problem.board.width * 1000 + 1e-3 and ys[-1] <= sim.problem.board.height * 1000 + 1e-3
    assert np.allclose(xs, np.arange(nx) * r.dx * 1000, atol=1e-3) and np.allclose(ys, np.arange(ny) * r.dy * 1000, atol=1e-3)
    # The same samples as the model's own coordinates, and the first rows hold the first node
    cx, cy = r.coords()
    assert float(rows[0]["x_mm"]) == pytest.approx(cx[0] * 1000) and float(rows[1]["x_mm"]) == pytest.approx(cx[1] * 1000, abs=1e-3)
    assert float(rows[0]["y_mm"]) == pytest.approx(cy[0] * 1000)


def test_fdm_surface_positions_are_the_grid_points(case):
    sim, d = case
    r = sim.results["fdm"]
    rows = read_dicts(d / "surface_fdm.csv")
    assert rows
    xs = {float(row["x_mm"]) for row in rows}
    cx, cy = r.coords()
    assert min(xs) == 0.0 and max(xs) == pytest.approx(sim.problem.board.width * 1000, abs=1e-3)
    assert max(float(row["y_mm"]) for row in rows) <= sim.problem.board.height * 1000 + 1e-3
    assert xs <= {round(float(v) * 1000, 4) for v in cx}


@pytest.mark.parametrize("model", ["fvm", "solid3d"])
def test_cell_fields_keep_the_cell_centres(case, model):
    sim, d = case
    r = sim.results[model]
    rows = read_dicts(d / f"field_{model}.csv")
    xs = sorted({float(row["x_mm"]) for row in rows})
    assert xs[0] == pytest.approx(0.5 * r.dx * 1000, abs=1e-3)
    assert xs[-1] == pytest.approx((r.T.shape[2] - 0.5) * r.dx * 1000, abs=1e-3)
    ys = sorted({float(row["y_mm"]) for row in rows})
    assert ys[0] == pytest.approx(0.5 * r.dy * 1000, abs=1e-3)
    if model == "fvm":
        srows = read_dicts(d / "surface_fvm.csv")
        assert min(float(x["x_mm"]) for x in srows) == pytest.approx(0.5 * r.dx * 1000, abs=1e-3)


def test_fdm_temperatures_and_layout_are_unchanged(case):
    sim, d = case
    r = sim.results["fdm"]
    rows = read_dicts(d / "field_fdm.csv")
    # Only the two position columns moved: the temperatures are the field itself, in the old order (layer, then y, then x), and the header is the old one
    with open(d / "field_fdm.csv", encoding="utf-8") as fh:
        assert fh.readline().strip() == "layer,x_mm,y_mm,T_c"
    got = np.array([float(row["T_c"]) for row in rows]).reshape(r.T.shape)
    assert np.array_equal(got, np.round(r.T, 4))
    with open(d / "surface_fdm.csv", encoding="utf-8") as fh:
        assert fh.readline().strip().split(",")[:7] == ["face", "x_mm", "y_mm", "T_surface_c", "T_surface_mean_c", "T_column_c", "upper_estimate"]


def test_fdm_positions_are_half_a_cell_below_the_old_ones(case):
    sim, d = case
    r = sim.results["fdm"]
    rows = read_dicts(d / "field_fdm.csv")
    ny, nx = r.T.shape[1:]
    old_x = (np.tile(np.arange(nx), ny * r.T.shape[0]) + 0.5) * r.dx * 1000
    new_x = np.array([float(row["x_mm"]) for row in rows])
    assert np.allclose(old_x - new_x, 0.5 * r.dx * 1000, atol=2e-4)
