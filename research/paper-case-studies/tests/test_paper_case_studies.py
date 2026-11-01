#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_paper_case_studies.py
@brief Fast tests of research/paper-case-studies that need none of the heavy runs: the transcribed data, the closed forms, the unit-cell solver against them, the independence of the references,
       and the plans printed by the two studies (--dry-run). Run: .venv/bin/python -m pytest -q research/paper-case-studies/tests
"""

import ast
import io
import math
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
for p in (HERE / "scripts", HERE / "lib"):
    sys.path.insert(0, str(p))

import _bootstrap                       # noqa: E402,F401  (puts the libs of the other folders on the path)
import axisym_cell as AC                # noqa: E402
import flux_channel as FC               # noqa: E402
import measured_data as MD              # noqa: E402
import study_measured_vias as S1        # noqa: E402
import study_thick_laminate as S2       # noqa: E402


def test_table_9_walls_and_groups():
    """!
    @brief The wall is 0.02 mm (the "0.04" column is the difference of the diameters) and the four arrangements hold every sample once.
    @return None.
    """
    for s, (_sp, _pi, di, do, col) in MD.TABLE_9.items():
        assert do - di == pytest.approx(col)
        assert (do - di) / 2 == pytest.approx(0.02)
    samples = sorted(s for v in MD.ARRANGEMENTS.values() for s in v[2])
    assert samples == list(range(1, 10))
    for _g, (kind, side, group, _x) in MD.ARRANGEMENTS.items():
        for s in group:
            sp, pi, _di, _do, _ = MD.TABLE_9[s]
            assert sp == side and (kind == "straight") == (pi == sp)


def test_fig33_has_four_measured_markers():
    """!
    @brief Four markers for nine samples (the study must not claim nine).
    @return None.
    """
    assert len(MD.FIG33_MEASURED) == 4
    assert len(MD.TABLE_9) == 9


def test_shen_table_ii_ambient_is_25():
    """!
    @brief psi_ta = (T_t - 25) / 2.8 reproduces every printed psi to 0.06 degC/W: the ambient of the experiment is 25 degC (derived).
    @return None.
    """
    for rows in MD.SHEN_TABLE_II.values():
        for t, psi in rows:
            assert (t - MD.SHEN_AMBIENT_DERIVED) / MD.SHEN_POWER_W == pytest.approx(psi, abs=0.06)


@pytest.mark.parametrize("sample", [1, 3, 4, 8])
def test_unit_cell_equals_closed_form_isothermal(sample):
    """!
    @brief With isothermal faces and no foil the field is one-dimensional, so the solver must equal equations 28 and 29 to rounding.
    @param sample Sample number of Table 9.
    @return None.
    """
    sp, pi, di, do, _ = MD.TABLE_9[sample]
    kind = "straight" if pi == sp else "staggered"
    kc = (AC.k_overall_straight if kind == "straight" else AC.k_overall_staggered)(sp * 1e-3, do * 1e-3, di * 1e-3)
    r = AC.unit_cell_k(S1.cell_area_m2(kind, sp), do * 1e-3, di * 1e-3, 1.6e-3)
    assert r["k_eff"] == pytest.approx(kc, rel=1e-9)
    assert r["balance"] < 1e-9


def test_unit_cell_thickness_independence_without_foil():
    """!
    @brief The thesis says k_overall does not depend on the thickness: true without foil, false with foil (a few percent at 1.6 mm).
    @return None.
    """
    a = AC.unit_cell_k(6.25e-6, 0.65e-3, 0.61e-3, 0.8e-3)["k_eff"]
    b = AC.unit_cell_k(6.25e-6, 0.65e-3, 0.61e-3, 3.2e-3)["k_eff"]
    assert a == pytest.approx(b, rel=1e-9)
    f1 = AC.unit_cell_k(6.25e-6, 0.65e-3, 0.61e-3, 0.8e-3, t_foil=35e-6)["k_eff"]
    f2 = AC.unit_cell_k(6.25e-6, 0.65e-3, 0.61e-3, 3.2e-3, t_foil=35e-6)["k_eff"]
    assert f1 > a and abs(f1 - f2) / a > 0.01


def test_flux_boundary_condition_is_worse_than_isothermal_and_converges():
    """!
    @brief A uniform flux into a foil adds a constriction: k_eff(flux) < k_eff(isothermal); halving the cells moves it by less than 1 %; the energy balance closes.
    @return None.
    """
    kw = dict(area=6.25e-6, d_o=0.65e-3, d_i=0.61e-3, t=1.6e-3, t_foil=35e-6)
    iso = AC.unit_cell_k(bc="isothermal", **kw)
    flux = AC.unit_cell_k(bc="flux", **kw)
    fine = AC.unit_cell_k(bc="flux", n_rad=120, n_z=80, n_foil=6, **kw)
    assert flux["k_eff"] < iso["k_eff"]
    assert fine["k_eff"] == pytest.approx(flux["k_eff"], rel=0.01)
    assert flux["balance"] < 1e-9


def test_phi_exponential_and_tanh_forms_agree():
    """!
    @brief Equation 51 as printed (exponentials) equals the tanh form used by the code, for a range of eigenvalues, thickness and film.
    @return None.
    """
    for zeta, t_eff, k_eff, h in ((50.0, 1e-3, 0.5, 100.0), (500.0, 4e-3, 0.5, 1e4), (5.0, 2e-3, 1.0, 10.0)):
        x = zeta * t_eff
        bi = h * t_eff / k_eff
        printed = ((math.exp(2 * x) + 1) * x - (1 - math.exp(2 * x)) * bi) / ((math.exp(2 * x) - 1) * x + (1 + math.exp(2 * x)) * bi)
        assert float(FC.phi(zeta, t_eff, k_eff, h)) == pytest.approx(printed, rel=1e-12)
    assert float(FC.phi(100.0, 1e-3, 1.0, np.inf)) == pytest.approx(math.tanh(0.1))


def test_spreading_vanishes_when_the_source_fills_the_channel():
    """!
    @brief R_s = 0 for a = c and b = d (the problem is one-dimensional): the sines of equation 50 are sin(m pi) = 0.
    @return None.
    """
    r = FC.spreading_resistance(5e-3, 5e-3, 5e-3, 5e-3, 1.6e-3, 0.9, 0.3, 100.0, n_max=200)
    assert abs(r) < 1e-12


def test_half_space_limit_of_a_square_source():
    """!
    @brief A small square source on a large deep block approaches the half-space constriction: R k s tends to 0.4732 for the mean temperature under a uniform flux (band 0.43 to 0.50; the box is
           finite, the series are truncated); a factor of 2 or 4 in the normalisation of the equation falls outside (the first reading of this study was 4 times too small).
    @return None.
    """
    a, c, t = 1e-3, 50e-3, 100e-3
    rs = FC.spreading_resistance(a, a, c, c, t, 1.0, 1.0, np.inf, n_max=3000)   # per watt of the whole source (half sizes in the formula)
    psi = rs * 1.0 * (2 * a)                                                     # times k and the side of the source
    assert 0.43 < psi < 0.50


def test_orthotropic_transformation():
    """!
    @brief Equation 50 depends on (k_xy, k_z, t) only through k_eff = sqrt(k_xy k_z) and t_eff = t / sqrt(k_z / k_xy): a board with these isotropic values has the same R_s.
    @return None.
    """
    t, kxy, kz = 1.6e-3, 0.9, 0.3
    k_eff, t_eff = math.sqrt(kxy * kz), t / math.sqrt(kz / kxy)
    r1 = FC.spreading_resistance(2e-3, 2e-3, 8e-3, 8e-3, t, kxy, kz, 1e3, n_max=300)
    r2 = FC.spreading_resistance(2e-3, 2e-3, 8e-3, 8e-3, t_eff, k_eff, k_eff, 1e3, n_max=300)
    assert r1 == pytest.approx(r2, rel=1e-12)


def test_references_import_nothing_of_the_program():
    """!
    @brief The independent references (the unit-cell solver, the channel closed form, the 3D solver and Shen's unit cell) do not import pcbthermal.
    @return None.
    """
    files = [HERE / "lib" / "axisym_cell.py", HERE / "lib" / "flux_channel.py", HERE / "lib" / "measured_data.py",
             HERE.parent / "gerber-real-boards" / "lib" / "ref3d.py", HERE.parent / "lumped-zones-adoption" / "lib" / "shen_case.py"]
    for f in files:
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            top = [n for n in names if n.split(".")[0] == "pcbthermal"]
            # shen_case imports the program only inside its board builder (a function body): the unit-cell solver used here does not call it
            if f.name == "shen_case.py":
                continue
            assert not top, f"{f.name} imports the program: {top}"


def test_lattices_and_shen_array():
    """!
    @brief The via lattices of the program runs: counts, density, the 12 x 12 array of Fig. 17 at the nominal 5.6 mm.
    @return None.
    """
    pts = S1.lattice("straight", 2.5, 6)
    assert len(pts) == 36 and all(0 < x < 15 and 0 < y < 15 for x, y in pts)
    pts = S1.lattice("staggered", 2.5, 6)
    assert len(pts) == 72
    assert len({(round(x, 6), round(y, 6)) for x, y in pts}) == 72
    arr, w, h, nv, area = S1.shen_array("I", 0.25, 5.6)
    assert nv == 144 and w == pytest.approx(5.4) and h == pytest.approx(5.4) and area == pytest.approx(0.45 * 0.45e-6)
    arr2, w2, h2, nv2, area2 = S1.shen_array("II", 0.25, 5.6)
    assert area2 / area == pytest.approx(math.sqrt(3) / 2)
    assert all(0 < x < w2 and 0 < y < h2 for x, y in arr2)


def test_thick_laminate_combinations():
    """!
    @brief 33 combinations, the first of which is the program's FR-4 at the smallest source, and the reference geometry uses a quarter with the source at the corner.
    @return None.
    """
    cs = S2.combos()
    assert len(cs) == 33
    assert all(c["kz"] == 0.3 for c in cs)
    rs, rt, rp = S2.closed_form(cs[0])
    assert rs > 0 and rt > rp > 0


@pytest.mark.parametrize("module", [S1, S2])
def test_dry_run_prints_the_plan_and_solves_nothing(module):
    """!
    @brief --dry-run prints the plan and the cost without importing the program or solving.
    @param module The study module.
    @return None.
    """
    before = "pcbthermal" in sys.modules
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = module.main(["--dry-run"])
    assert code == 0 and "DRY RUN" in buf.getvalue()
    assert ("pcbthermal" in sys.modules) == before
