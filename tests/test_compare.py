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


def _fem_table():
    """!
    @brief The peak table of docs/validation.md 56.1 as {board: (FVM rise, FEM rise)} for the boards that have both (the FEM skips the round outline).
    @return dict.
    """
    text = open(os.path.join(ROOT, "docs", "validation.md"), encoding="utf-8").read()
    sec = text.split("### 56.1 Every board, every model (peak and part mean)", 1)[1].split("Part mean under the first part", 1)[0]
    out = {}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.match(r"[-\d.]+ \(", cells[1]) and re.match(r"[\d.]+$", cells[6]):
            out[cells[0]] = (float(cells[1].split()[0]), float(cells[6]))
    return out


def test_every_documented_range_is_what_the_validation_table_prints():
    """!
    @brief The ranges of `compare.EXPECTED` are recomputed from the 20 scenarios of docs/validation.md section 2 (the FEM row: from the 16 boards of 56.1): the range,
           the count inside it and each outlier.
    """
    cols = _scenario_table()
    for (model, ref), tip in compare.EXPECTED.items():
        assert ref == "fvm"
        if model == "fem":
            continue
        vals = cols[model]
        assert len(vals) == tip.n_all == 20
        outliers = {round(v, 1) for _what, v in tip.outliers}
        inside = [v for v in vals if round(v, 1) not in outliers]
        assert len(inside) == tip.n, model
        assert (min(inside), max(inside)) == (tip.lo, tip.hi), model
        for _what, v in tip.outliers:
            assert any(abs(x - v) < 1e-9 for x in vals), (model, v)


def test_the_fem_row_is_what_validation_56_1_prints():
    """!
    @brief FEM - FVM, the view's convention (the share of the rise of the reference, the FVM): recomputed from the peaks (rises) of the 56.1 table on the 19 boards with a
           FEM value, the range is -2.7 to +0.3 % on 18 boards and the L of drawn copper is the one case outside; the validation text gives the FVM against the FEM
           (share of the FEM rise) as -0.3 to +2.7 % without the drawn boards, the same boards with the sign and the denominator converted.
    """
    rows = _fem_table()
    shares = {b: 100.0 * (fem / fvm - 1.0) for b, (fvm, fem) in rows.items()}
    tip = compare.EXPECTED[("fem", "fvm")]
    assert len(shares) == tip.n_all == 19
    outliers = {round(v, 1) for _what, v in tip.outliers}
    inside = [v for v in shares.values() if round(v, 1) not in outliers]
    assert len(inside) == tip.n == 18
    assert (round(min(inside), 1), round(max(inside), 1)) == (tip.lo, tip.hi)
    assert round(shares["drawn_ell"], 1) == tip.outliers[0][1] == -15.1
    plain = [v for b, v in shares.items() if not b.startswith("drawn_")]
    assert (round(min(plain), 1), round(max(plain), 1)) == (tip.lo, tip.hi)           # The same range as the 16 boards of the summary row below
    assert "section 56.1" in tip.evidence
    text = open(os.path.join(ROOT, "docs", "validation.md"), encoding="utf-8").read()
    assert "| without the three drawn boards | 1 | FVM | peak | 16 | 0.86 | 2.74 (one_layer_pad) | -0.3 to +2.7 |" in text   # The summary row the range converts


def test_the_verdict_is_usual_inside_the_range_and_outside_it_says_so():
    """!
    @brief The line begins with the verdict; the flag is on only outside the documented range (judged on the value as shown, one decimal); the tooltip holds the range,
           the cases, the cases outside, the evidence and the sentence that the number is the hottest point.
    """
    inside = compare.expected_agreement("lumped", "fvm", 1.4, 2.4)
    assert inside.line == "Usual for the LPTN: hottest point +1.4 K, +2.4 % of the rise (usual -5.4 to +8.4 %)" and not inside.outside
    assert "19 of 20 scenarios" in inside.tooltip and "a copper edge across the heater -27.9 %" in inside.tooltip
    assert "docs/validation.md sections 1 and 2" in inside.tooltip and inside.tooltip.endswith("the map can differ more around the parts.")
    assert not compare.expected_agreement("lumped", "fvm", 5.0, 8.4).outside and not compare.expected_agreement("lumped", "fvm", -3.0, -5.4).outside
    out = compare.expected_agreement("lumped", "fvm", 17.0, 27.9)
    assert out.outside and out.line.startswith("Outside the usual range for the LPTN: hottest point +17.0 K, +27.9 % of the rise")
    assert compare.expected_agreement("lumped", "fvm", -3.0, -5.5).outside                 # Below the lowest of the range
    fdm = compare.expected_agreement("fdm", "fvm", -0.1, -0.1)
    assert fdm.line == "Usual for the FDM: hottest point -0.1 K, -0.1 % of the rise (usual -0.5 to 0.0 %)" and not fdm.outside
    assert compare.expected_agreement("fdm", "fvm", 0.6, 0.5).outside
    ana = compare.expected_agreement("analytic", "fvm", -0.7, -1.1)
    assert ana.line.startswith("Usual for the Analytic: hottest point -0.7 K, -1.1 % of the rise (usual -1.8 to +0.3 %)")
    fem = compare.expected_agreement("fem", "fvm", -1.0, -1.6)
    assert fem.line == "Usual for the FEM: hottest point -1.0 K, -1.6 % of the rise (usual -2.7 to +0.3 %)" and not fem.outside and "section 56.1" in fem.tooltip


def test_a_pair_without_documented_evidence_has_no_line():
    """!
    @brief Any pair whose reference is not the FVM, and a model that is not in the table, have no line: where the evidence is thin the view is silent.
    """
    assert compare.expected_agreement("lumped", "analytic", 1.0, 1.0) is None and compare.expected_agreement("fvm", "fvm", 0.0, 0.0) is None
    assert compare.expected_agreement("fvm", "fem", 1.0, 1.0) is None
    assert compare.expected_agreement("lumped", "fvm", 1.0, 1.0).tooltip.count("sections 1 and 2") == 1


def test_a_run_at_another_cell_gets_no_verdict():
    """!
    @brief The ranges were measured with 1 mm cells and the gap between two models moves with the cell (FDM - FVM on the example board: -1.1 % of the rise at 2 mm,
           outside the 1 mm range). A run at another cell gets no verdict and never the warning flag: the line says it is not judged and names the cell of the range;
           a run at 1 mm (to 1 %) or one that does not state its cell is judged.
    """
    coarse = compare.expected_agreement("fdm", "fvm", -0.7, -1.1, 2.0)
    assert not coarse.outside and coarse.line == "Not judged at 2 mm cells: FDM hottest point -0.7 K, -1.1 % of the rise (usual -0.5 to 0.0 % at 1 mm)"
    assert "measured with 1 mm cells; this run used 2 mm" in coarse.tooltip and "no verdict" in coarse.tooltip
    assert not compare.expected_agreement("lumped", "fvm", 17.0, 27.9, 0.5).outside                       # Not even a large gap is flagged at another cell
    assert compare.expected_agreement("lumped", "fvm", 17.0, 27.9, 1.0).outside
    assert compare.expected_agreement("lumped", "fvm", 17.0, 27.9, 1.005).outside                     # A cell of 1 mm written with round-off is 1 mm
    assert compare.expected_agreement("fdm", "fvm", -0.1, -0.1, 1.0).line.startswith("Usual for the FDM")
    assert "measured with 1 mm cells" not in compare.expected_agreement("fdm", "fvm", -0.1, -0.1, 1.0).tooltip
    assert "measured with 1 mm cells" not in compare.expected_agreement("fdm", "fvm", -0.1, -0.1).tooltip


def test_the_fdm_and_fvm_at_2_mm_give_the_gap_that_motivates_the_rule(sim):
    """!
    @brief The example board at 2 mm (the module fixture): the FDM's hottest point is outside the 1 mm range of the FDM against the FVM, and the view says 'not judged'
           rather than 'outside'. Guards the measurement quoted in the docstring of `expected_agreement` and in the user guide.
    @param sim Simulation fixture (2 mm cells).
    """
    d = compare.difference_field(sim.results["fdm"], sim.results["fvm"], sim.problem)
    assert round(d.peak_pct, 1) == -1.1
    a = compare.expected_agreement(d.model, d.reference, d.peak_k, d.peak_pct, 1000.0 * d.dx)
    assert not a.outside and a.line.startswith("Not judged at 2 mm cells")
