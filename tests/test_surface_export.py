#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_surface_export.py
@brief The surface read-out in the exports: surface_<model>.csv keeps its seven earlier columns and appends the model, the kind and the FEM node value; the new hotspots, zones and
       parts tables name the read-out of every temperature; the hotspot points carry the surface and the point value of the same cell without moving any column value; the
       statistics of the Difference view go to a small CSV; the window's export entries write them.
"""

import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import analysis, compare, thickness
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board

MODELS = ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")
LEGACY_SURFACE_HEADER = ["face", "x_mm", "y_mm", "T_surface_c", "T_surface_mean_c", "T_column_c", "upper_estimate"]


@pytest.fixture(scope="module")
def sim():
    """!
    @brief The example board in every model that can hold a surface, at a coarse cell (the tests read arrays, not accuracy).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=MODELS, cell_mm=2.0, hotspot_c=40.0))


def read(path):
    """!
    @brief Read a CSV file as a header and rows of strings.
    @param path File path.
    @return Tuple (header, rows).
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def legacy_surface_rows(r):
    """!
    @brief The rows that the writer of every earlier version made for a result (the first seven columns), re-implemented here as the reference of the compatibility test.
    @details The positions are the sample positions of the field (cell centres; the grid points of a node field, the FDM, since the correction of its export positions).
    @param r SteadyResult with the surface arrays.
    @return List of lists of the seven values.
    """
    out = []
    off = 0.0 if r.grid == "nodes" else 0.5
    for face, tag, layer in ((0, "top", 0), (1, "bottom", r.T.shape[0] - 1)):
        for i in range(r.T.shape[1]):
            for j in range(r.T.shape[2]):
                if np.isfinite(r.arrays["T_surface"][face, i, j]):
                    out.append([tag, round((j + off) * r.dx * 1000, 4), round((i + off) * r.dy * 1000, 4), round(float(r.arrays["T_surface"][face, i, j]), 4),
                                round(float(r.arrays["T_surface_mean"][face, i, j]), 4), round(float(r.T[layer, i, j]), 4), int(r.arrays["T_surface_flag"][face, i, j])])
    return out


def test_field_csv_is_the_old_format(sim, tmp_path):
    sim.save(str(tmp_path), plots=False)
    for name, r in sim.results.items():
        if r.T is None:
            continue
        head, rows = read(tmp_path / f"field_{name}.csv")
        assert head == ["layer", "x_mm", "y_mm", "T_c"]
        assert len(rows) == r.T.size
        assert float(rows[0][3]) == pytest.approx(float(r.T[0, 0, 0]), abs=1e-4)


@pytest.mark.parametrize("model", [m for m in MODELS if m != "lumped"])
def test_surface_csv_old_columns_first_and_new_ones_appended(sim, tmp_path, model):
    r = sim.results[model]
    if "T_surface" not in r.arrays:
        pytest.skip(f"{model} holds no surface on this board")
    sim.save(str(tmp_path), plots=False, surface_files=True)
    head, rows = read(tmp_path / f"surface_{model}.csv")
    # An old reader that takes the first seven columns by position or by name still works: same names, same order, same values
    assert head[:7] == LEGACY_SURFACE_HEADER and head[7:] == ["model", "surface_kind", "T_point_c"]
    legacy = legacy_surface_rows(r)
    assert len(rows) == len(legacy) > 0
    for new, old in zip(rows, legacy):
        assert [new[0]] + [float(v) for v in new[1:7]] == [old[0]] + [float(v) for v in old[1:]]
    # The new columns: the model, the kind of the read-out of the face, the FEM node value
    face_of = {"top": 0, "bottom": 1}
    assert {row[7] for row in rows} == {model}
    for row in rows[:: max(len(rows) // 50, 1)]:
        assert row[8] == thickness.surface_kind(r, face_of[row[0]])
    if model == "fem":
        row = rows[0]
        assert row[9] != ""
        # the node value of the first cell of the file is arrays["T_point"] of that cell
        first = np.argwhere(np.isfinite(r.arrays["T_surface"][0]))[0]
        assert float(row[9]) == pytest.approx(float(r.arrays["T_point"][0, first[0], first[1]]), abs=1e-4)
    else:
        assert all(row[9] == "" for row in rows)


def test_the_lumped_has_no_surface_file(sim, tmp_path):
    sim.save(str(tmp_path), plots=False, surface_files=True)
    assert not (tmp_path / "surface_lumped.csv").exists()


def test_surface_files_stay_opt_in_for_the_library(sim, tmp_path):
    sim.save(str(tmp_path), plots=False)
    assert not list(tmp_path.glob("surface_*.csv"))


def test_hotspot_rows_keep_every_column_value_and_add_the_siblings(sim):
    for name, r in sim.results.items():
        if r.T is None:
            continue
        hs = analysis.hotspots(r, 40.0)
        assert hs, name
        for h in hs:
            assert h["readout"] == "column"
            l = h["layer"] - 1
            # The column value is the field at the point the row names (cell centre or node)
            j = int(round(h["x_mm"] / 1000.0 / r.dx - (0.0 if r.grid == "nodes" else 0.5)))
            i = int(round(h["y_mm"] / 1000.0 / r.dy - (0.0 if r.grid == "nodes" else 0.5)))
            assert h["t_max"] == pytest.approx(float(r.T[l, i, j]), abs=1e-9)
            outer = l in (0, r.T.shape[0] - 1)
            face = 0 if l == 0 else 1
            # The surface and the node are the maxima over the hot area (the connected region of the row), independently re-labelled here
            from scipy import ndimage
            lab, _n = ndimage.label(r.T[l] > 40.0)
            region = lab == lab[i, j]
            if outer and "T_surface" in r.arrays and np.isfinite(r.arrays["T_surface"][face][region]).any():
                assert h["t_surface"] == pytest.approx(float(np.nanmax(np.where(region, r.arrays["T_surface"][face], np.nan))), abs=1e-12)
                assert h["t_surface"] >= float(r.arrays["T_surface"][face, i, j]) - 1e-12 if np.isfinite(r.arrays["T_surface"][face, i, j]) else True
                assert h["surface_kind"] == thickness.surface_kind(r, face)
            else:
                assert h["t_surface"] is None and h["surface_kind"] is None
            if name == "fem" and outer:
                assert h["t_point"] == pytest.approx(float(np.nanmax(np.where(region, r.arrays["T_point"][face], np.nan))), abs=1e-12)
            else:
                assert h["t_point"] is None


def test_hotspot_surface_and_node_are_the_hottest_of_the_area_not_of_one_cell(sim):
    # Review: the first version read the surface and the node in the cell of the column maximum only; a hotter face elsewhere in the same hot area was then hidden behind a
    # header that says Tmax. A copy of the FEM result gets a hotter surface and node in another cell of the area: the row must report them, and keep its column point.
    import copy
    from scipy import ndimage
    r = copy.deepcopy(sim.results["fem"])
    base = analysis.hotspots(r, 40.0)[0]
    lab, _n = ndimage.label(r.T[0] > 40.0)
    j0 = int(round(base["x_mm"] / 1000.0 / r.dx - 0.5))
    i0 = int(round(base["y_mm"] / 1000.0 / r.dy - 0.5))
    ii, jj = np.nonzero(lab == lab[i0, j0])
    k = next(n for n in range(len(ii)) if (ii[n], jj[n]) != (i0, j0))
    r.arrays["T_surface"][0, ii[k], jj[k]] = base["t_max"] + 7.0
    r.arrays["T_point"][0, ii[k], jj[k]] = base["t_max"] + 9.0
    row = analysis.hotspots(r, 40.0)[0]
    assert row["t_surface"] == pytest.approx(base["t_max"] + 7.0) and row["t_point"] == pytest.approx(base["t_max"] + 9.0)
    assert (row["x_mm"], row["y_mm"], row["t_max"]) == (base["x_mm"], base["y_mm"], base["t_max"])


def test_hotspot_points_are_the_same_with_and_without_the_new_keys(sim):
    # Which points are found must not depend on the new keys: the old four values equal an independent connected-region search
    from scipy import ndimage
    r = sim.results["fvm"]
    hs = analysis.hotspots(r, 40.0)
    n = 0
    for l in range(r.T.shape[0]):
        lab, k = ndimage.label(r.T[l] > 40.0)
        n += k
    assert len(hs) == n
    assert hs == sorted(hs, key=lambda x: -x["t_max"])


def test_zone_rows_and_parts_get_the_surface_beside_the_column(sim):
    for name, r in sim.results.items():
        if r.T is None:
            continue
        for z in analysis.zone_stats(r, sim.problem):
            assert z["t_max"] >= z["t_mean"] - 1e-9
            if z["layer"] in (1, sim.problem.board.layers) and "T_surface" in r.arrays:
                assert z["surface_kind"] == thickness.surface_kind(r, 0 if z["layer"] == 1 else 1)
            else:
                assert z["t_max_surface"] is None


def test_statistics_files(sim, tmp_path):
    sim.save(str(tmp_path), plots=False)
    ref = sim.reference.model
    head, rows = read(tmp_path / f"hotspots_{ref}.csv")
    assert head == ["model", "rank", "layer", "x_mm", "y_mm", "area_mm2", "T_max_column_c", "T_max_surface_c", "surface_kind", "T_max_point_c"]
    hs = analysis.hotspots(sim.reference, sim.options.hotspot_c)
    assert len(rows) == len(hs)
    assert float(rows[0][6]) == pytest.approx(hs[0]["t_max"], abs=1e-4)
    head, rows = read(tmp_path / f"parts_{ref}.csv")
    assert head[:6] == ["model", "part", "layer", "power_w", "T_mean_column_c", "T_max_column_c"] and "T_max_surface_c" in head
    for row, h in zip(rows, sim.heater_rows()):
        assert row[1] == h["name"] and float(row[5]) == pytest.approx(h["t_max"], abs=1e-4)
        assert float(row[7]) == pytest.approx(h["t_max_surface"], abs=1e-4)          # the FVM has the surface beside the column
    assert (tmp_path / f"zones_{ref}.csv").exists() == bool(sim.problem.zones)


def test_part_points_only_for_the_fem(sim):
    assert all(p is None for p in sim.part_points())
    fem_only = simulate(example_board(), SolverOptions(models=("fem",), cell_mm=2.0))
    pts = fem_only.part_points()
    assert pts and all(p is not None for p in pts)
    # A node value is a different quantity from the cell mean: it is at least the column max of the part (the hottest node of its cells is not below the mean of its element)
    assert pts[0] >= fem_only.heater_rows()[0]["t_max"] - 1e-9


def test_report_names_the_readouts(sim):
    text = sim.report()
    assert "(column) at (" in text
    assert "column mean" in text and "column max" in text


def test_difference_statistics_csv(sim, tmp_path):
    d = compare.difference_field(sim.results["fdm"], sim.results["fvm"], sim.problem, compare.COLUMN, 0)
    ag = compare.expected_agreement(d.model, d.reference, d.peak_k, d.peak_pct, 2.0)
    p = compare.write_statistics_csv(str(tmp_path / "d.csv"), d, 2.0, ag)
    head, rows = read(p)
    assert head == compare.STATISTICS_HEADER and len(rows) == 1
    row = dict(zip(head, rows[0]))
    assert row["model"] == "FDM" and row["reference"] == "FVM" and row["readout"] == "layer 1, column mean"
    assert float(row["max_k"]) == pytest.approx(d.maximum, abs=1e-6) and float(row["min_k"]) == pytest.approx(d.minimum, abs=1e-6)
    assert float(row["rms_k"]) == pytest.approx(d.rms, abs=1e-6) and float(row["mean_k"]) == pytest.approx(d.mean, abs=1e-6)
    assert (float(row["max_x_mm"]), float(row["max_y_mm"])) == pytest.approx(d.where_max, abs=1e-3)
    # At 2 mm (not the documented 1 mm cell) the view gives no verdict: the line says 'Not judged' and the flag is blank, never a 0 that would read as 'usual' (review)
    assert row["verdict"] == ag.line and row["verdict"].startswith("Not judged") and row["outside_usual_range"] == "" and float(row["cell_mm"]) == 2.0
    # An independent recomputation (review: the first version went through the library's own sampler): the FDM node field interpolated bilinearly by SciPy onto the FVM cell centres
    from scipy.interpolate import RegularGridInterpolator
    fd, fv = sim.results["fdm"], sim.results["fvm"]
    xn, yn = fd.coords()
    xc, yc = fv.coords()
    Y, X = np.meshgrid(yc, xc, indexing="ij")
    diff = RegularGridInterpolator((yn, xn), fd.T[0])(np.stack([Y.ravel(), X.ravel()], -1)).reshape(Y.shape) - fv.T[0]
    assert np.sqrt(np.mean(diff ** 2)) == pytest.approx(float(row["rms_k"]), abs=1e-6)
    assert float(diff.max()) == pytest.approx(float(row["max_k"]), abs=1e-6) and float(diff.mean()) == pytest.approx(float(row["mean_k"]), abs=1e-6)
    # At the documented cell the flag is given
    row1 = compare.statistics_row(d, 1.0, compare.expected_agreement(d.model, d.reference, d.peak_k, d.peak_pct, 1.0))
    assert row1[compare.STATISTICS_HEADER.index("outside_usual_range")] in (0, 1)


def test_difference_statistics_surface_and_no_verdict(sim, tmp_path):
    d = compare.difference_field(sim.results["fem"], sim.results["fvm"], sim.problem, compare.SURFACE, 0, 0)
    head, rows = read(compare.write_statistics_csv(str(tmp_path / "s.csv"), d, None, None))
    row = dict(zip(head, rows[0]))
    assert row["readout"] == "surface (top)" and row["face"] == "top" and row["verdict"] == "" and row["outside_usual_range"] == "" and row["cell_mm"] == ""
