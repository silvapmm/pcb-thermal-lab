#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_compare.py
@brief Tests of `pcbthermal.compare`, the data of the Difference view: zero for the same model, antisymmetry, the mean of the difference, the interpolation on a
       linear field, the refusal to mix read-outs, and the documented numbers of the expected-agreement statements against the table of docs/validation.md.
"""

import copy
import os
import re

import numpy as np
import pytest

from pcbthermal import compare
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.results import SteadyResult

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def sim():
    """!
    @brief The example board in four models at a 2 mm cell (the FDM is a node field: another grid).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped", "analytic", "fdm"), cell_mm=2.0))


def _plain(field, dx=0.001, grid="cells", model="fvm", surface=None):
    """!
    @brief A SteadyResult that holds one field, for the pure functions.
    @param field Array (ny, nx) of degC, one layer.
    @param dx Spacing in metres (both axes).
    @param grid "cells" or "nodes".
    @param model Model key.
    @param surface Optional array (2, ny, nx) of the surface read-out.
    @return SteadyResult.
    """
    r = SteadyResult(model=model, ambient=25.0, power_in=1.0, t_max=float(np.max(field)), t_min=float(np.min(field)), t_mean=float(np.mean(field)),
                     layer_mean=[float(np.mean(field))], T=np.asarray(field, float)[None], dx=dx, dy=dx, grid=grid)
    if surface is not None:
        r.arrays["T_surface"] = np.asarray(surface, float)
    return r


def test_the_same_model_gives_zero_and_two_models_are_antisymmetric(sim):
    """!
    @brief model - model is 0 everywhere; A - B is B - A with the sign changed, on the same grid.
    @param sim Simulation fixture.
    """
    fvm, lum, ana = sim.results["fvm"], sim.results["lumped"], sim.results["analytic"]
    clone = copy.deepcopy(fvm)
    d0 = compare.difference_field(clone, fvm, sim.problem)       # An equal copy: not the same object, the same numbers
    assert np.nanmax(np.abs(d0.values)) == 0.0 and d0.rms == 0.0 and not d0.resampled
    ab = compare.difference_field(lum, ana, sim.problem)
    ba = compare.difference_field(ana, lum, sim.problem)
    assert np.allclose(ab.values, -ba.values, equal_nan=True)
    assert ab.maximum == pytest.approx(-ba.minimum) and ab.rms == pytest.approx(ba.rms)
    assert compare.unavailable_reason(fvm, fvm, sim.problem) is not None           # The very same result: refused with a reason


def test_mean_difference_is_the_difference_of_the_means(sim):
    """!
    @brief On one grid the mean of the difference equals the difference of the layer means.
    @param sim Simulation fixture.
    """
    d = compare.difference_field(sim.results["lumped"], sim.results["fvm"], sim.problem, layer=0)
    assert d.mean == pytest.approx(sim.results["lumped"].layer_mean[0] - sim.results["fvm"].layer_mean[0], abs=1e-6)
    assert d.limit >= max(abs(d.maximum), abs(d.minimum))                          # Symmetric scale: zero is the middle
    assert d.peak_k == pytest.approx(sim.results["lumped"].t_max - sim.results["fvm"].t_max)


def test_a_linear_field_is_resampled_exactly_between_a_node_and_a_cell_grid():
    """!
    @brief A plane read on cell centres and on grid points, subtracted: zero to round-off (bilinear interpolation is exact for a linear field, also in the half cell at the edges).
    """
    nx, ny, dx = 20, 12, 0.002
    plane = lambda x, y: 30.0 + 400.0 * x + 250.0 * y
    xc, yc = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    xn, yn = np.arange(nx + 1) * dx, np.arange(ny + 1) * dx
    cells = _plain(plane(*np.meshgrid(xc, yc)), dx, "cells", "fvm")
    nodes = _plain(plane(*np.meshgrid(xn, yn)), dx, "nodes", "fdm")
    diff, moved = compare.subtract(compare.sample(nodes), compare.sample(cells))      # nodes onto the cell grid
    assert moved and np.abs(diff).max() < 1e-9
    diff2, moved2 = compare.subtract(compare.sample(cells), compare.sample(nodes))    # cells onto the node grid (extrapolated in the half cell at the edge)
    assert moved2 and np.abs(diff2).max() < 1e-9


def test_another_cell_size_is_resampled_and_the_note_says_so(sim):
    """!
    @brief The FDM (nodes) minus the FVM (cells) is interpolated and carries the note; two fields on one grid carry none (the LPTN may have its own raster too).
    @param sim Simulation fixture.
    """
    d = compare.difference_field(sim.results["fdm"], sim.results["fvm"], sim.problem)
    assert d.resampled and d.values.shape == sim.results["fvm"].T[0].shape
    assert any("interpolated" in n for n in d.notes)
    assert not compare.difference_field(copy.deepcopy(sim.results["fvm"]), sim.results["fvm"], sim.problem).notes      # One grid: nothing to say


def test_two_read_outs_are_never_mixed():
    """!
    @brief A column against a surface is refused, and a model without a surface read-out is refused for the surface (the message names the model).
    """
    f = np.full((4, 5), 40.0)
    col = compare.sample(_plain(f))
    surf = compare.sample(_plain(f, surface=np.stack([f, f])), compare.SURFACE)
    with pytest.raises(compare.DifferenceError, match="definition"):
        compare.subtract(col, surf)
    with pytest.raises(compare.DifferenceError, match="LPTN has no surface"):
        compare.sample(_plain(f, model="lumped"), compare.SURFACE)
    with pytest.raises(compare.DifferenceError, match="no temperature field"):
        compare.sample(SteadyResult(model="fvm", ambient=25.0, power_in=0.0, t_max=25.0, t_min=25.0, t_mean=25.0, layer_mean=[25.0]))


def test_surface_difference_uses_the_surface_of_both(sim):
    """!
    @brief The FVM and FDM both hold a surface read-out: the difference is of surfaces, named as such, on the layer that owns the face.
    @param sim Simulation fixture.
    """
    d = compare.difference_field(sim.results["fdm"], sim.results["fvm"], sim.problem, readout=compare.SURFACE, face=0)
    assert d.readout == "surface" and d.layer == 0 and "surface (top)" in compare.readout_name(d.readout, d.layer, d.face)
    assert compare.unavailable_reason(sim.results["lumped"], sim.results["fvm"], sim.problem, compare.SURFACE) is not None


def test_default_reference_is_the_fvm_else_the_first_other_model():
    """!
    @brief The default reference: the FVM, never the model itself; with no FVM the first other model with a field.
    """
    f = np.zeros((2, 2))
    res = {"fdm": _plain(f, model="fdm"), "fvm": _plain(f), "lumped": _plain(f, model="lumped")}
    assert compare.default_reference(res, "fdm") == "fvm"
    assert compare.default_reference(res, "fvm") == "fdm"
    res.pop("fvm")
    assert compare.default_reference(res, "fdm") == "lumped"
    assert compare.default_reference({"fvm": _plain(f)}, "fvm") is None


def _scenario_table():
    """!
    @brief The 20 rows of the scenario table of docs/validation.md section 2 as {model: [percent, ...]}.
    @return dict with keys fdm, solid3d, lumped, analytic (percent of the rise against the FVM, one per scenario).
    """
    text = open(os.path.join(ROOT, "docs", "validation.md"), encoding="utf-8").read()
    sec = text.split("## 2. Many scenarios, every model", 1)[1].split("*Audit of 2.8.0", 1)[0]
    cols = {"fdm": [], "solid3d": [], "lumped": [], "analytic": []}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.match(r"[-\d.]+ \(", cells[2]):
            for k, c in zip(("fdm", "solid3d", "lumped", "analytic"), cells[2:6]):
                cols[k].append(float(re.search(r"\(([-+]?\d+\.\d) %\)", c).group(1)))
    return cols


def test_every_documented_range_is_what_the_validation_table_prints():
    """!
    @brief The ranges of `compare.EXPECTED` are recomputed from the 20 scenarios of docs/validation.md section 2: the range, the count inside it and each outlier.
    """
    cols = _scenario_table()
    for (model, ref), tip in compare.EXPECTED.items():
        assert ref == "fvm"
        vals = cols[model]
        assert len(vals) == tip.n_all == 20
        outliers = {round(v, 1) for _what, v in tip.outliers}
        inside = [v for v in vals if round(v, 1) not in outliers]
        assert len(inside) == tip.n, model
        assert (min(inside), max(inside)) == (tip.lo, tip.hi), model
        for _what, v in tip.outliers:
            assert any(abs(x - v) < 1e-9 for x in vals), (model, v)


def test_a_pair_without_documented_evidence_says_nothing():
    """!
    @brief The FEM and any pair whose reference is not the FVM have no statement: where the evidence is thin the view is silent.
    """
    assert compare.expected_agreement("fem", "fvm") == [] and compare.expected_agreement("lumped", "analytic") == []
    assert compare.expected_agreement("lumped", "fvm")[-1].endswith("sections 1 and 2)")
