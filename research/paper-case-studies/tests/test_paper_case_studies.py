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
    @brief A small square source on a large deep block approaches the half-space constriction. The exact value is computed here independently: for a uniform flux the mean temperature of the source
           is q / (2 pi k A) times the double integral of 1/r over the square, so R k s = I / (2 pi) with I = 4 int_0^1 int_0^1 (1 - u)(1 - v) / sqrt(u^2 + v^2) du dv (the mean reciprocal distance
           of a unit square, 2.9732: R k s = 0.4732). The series must lie between 95 % and 100 % of it for a box of 50 a and a depth of 100 a (finite box, truncated series); a factor of 2 or 4 in the
           normalisation falls outside (the first reading of this study was 4 times too small).
    @return None.
    """
    from scipy.integrate import dblquad
    integral, _err = dblquad(lambda v, u: (1 - u) * (1 - v) / math.hypot(u, v), 0, 1, 0, 1)
    exact = 4.0 * integral / (2.0 * math.pi)
    assert exact == pytest.approx(0.4732, abs=2e-4)
    a, c, t = 1e-3, 50e-3, 100e-3
    rs = FC.spreading_resistance(a, a, c, c, t, 1.0, 1.0, np.inf, n_max=3000)   # per watt of the whole source (half sizes in the formula)
    psi = rs * 1.0 * (2 * a)                                                     # times k and the side of the source
    assert 0.95 * exact < psi < exact


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
        # shen_case imports the program only inside its board builder (a function body): for it the module level and the body of `unit_cell` (the function used here) are checked;
        # for the others every import anywhere in the file
        if f.name == "shen_case.py":
            scopes = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            scopes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unit_cell"]
            assert len(scopes) > 0 and any(isinstance(n, ast.FunctionDef) and n.name == "unit_cell" for n in scopes)
            nodes = [m for n in scopes for m in ast.walk(n)]
        else:
            nodes = list(ast.walk(tree))
        for node in nodes:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            top = [n for n in names if n.split(".")[0] == "pcbthermal"]
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


@pytest.mark.parametrize("eps", [0.02, 0.1, 0.25, 0.5])
def test_deep_channel_against_published_correlation(eps):
    """!
    @brief Equation 50 for a deep isotropic square channel is equation 19 of Yovanovich, Muzychka and Culham (1999, J. Thermophys. Heat Transfer 13 (4), page 498, read from the page image),
           whose published correlation (equation 20, page 499) is k sqrt(A_s) R_s = 0.47320 - 0.62075 eps + 0.1198 eps^3 with a maximum error of about 0.3 % for 0 <= eps <= 0.5. This checks
           the normalisation of R_s (per watt of the whole source) against a published number, not only against the half-space integral.
    @param eps Relative source size a / c.
    @return None.
    """
    c = 10e-3
    a = eps * c
    rs = FC.spreading_resistance(a, a, c, c, 4 * c, 1.0, 1.0, np.inf, n_max=3000)
    published = 0.47320 - 0.62075 * eps + 0.1198 * eps ** 3
    assert rs * 1.0 * (2 * a) == pytest.approx(published, rel=0.003)


def test_shen_network_inversion_is_exact_and_eq42_is_not():
    """!
    @brief The bottom-path resistance from psi_ta (Shen Fig. 22 (b)) inverts the forward network exactly; the paper's equation 42 (psi (1 + theta_jt / theta_ta)) differs from it by the
           dropped 1 / theta_ta term (several percent at the theta_ta of Fig. 20), and theta_ta below psi has no network (an earlier draft swept 20 to 40 degC/W).
    @return None.
    """
    for th in MD.SHEN_THETA_TA_SWEEP:
        for rows in MD.SHEN_TABLE_II.values():
            for _t, psi in rows:
                sig = S1.sigma_from_psi(psi, th)
                assert S1.psi_from_sigma(sig, th) == pytest.approx(psi, rel=1e-12)
                eq42 = psi * (1.0 + MD.SHEN_THETA_JT / th)
                assert sig > eq42 * 1.03
    with pytest.raises(ValueError):
        S1.sigma_from_psi(17.5, 17.0)
    assert S1.predicted_contrast(15.0, 0.0, 370.0) == pytest.approx(0.0, abs=1e-12)


def test_reference_reads_at_the_face_like_equation_50():
    """!
    @brief With the source over the whole channel the problem is one-dimensional and R_s = 0: the 3D reference plus its face term must give R' = t / (k_z W^2) exactly (bare laminate), and the
           reading at the node alone would be short by (t_cu / 2) / (k_z W^2). Tiny grid (4 x 4 pixels, 16 sub-slabs): milliseconds.
    @return None.
    """
    c = {"S": 4.0, "W": 4.0, "t": 1.6, "kxy": 0.9, "kz": 0.3, "h": 1.0e3}
    r = S2.reference_3d(c, px_div=8, n_sub=16)
    exact = 1.6e-3 / (0.3 * (4e-3) ** 2)
    assert r == pytest.approx(exact, rel=1e-9)
    rs, _rt, rp = S2.closed_form(c, n_max=200)
    assert abs(rs) < 1e-12 and rp == pytest.approx(exact, rel=1e-12)


def test_extrapolated_reference_agrees_with_equation_50():
    """!
    @brief The extrapolated 3D reference (Richardson in the sub-slabs, quadratic in 1/pixels) is within 1 % of equation 50 on a cheap case (S = 5 mm on 20 mm, t = 1.6 mm, h = 1e3), where the single grid S/16 was 0.8 % high and S/8 more.
    @return None.
    """
    c = {"S": 5.0, "W": 20.0, "t": 1.6, "kxy": 0.9, "kz": 0.3, "h": 1.0e3}
    rp = S2.closed_form(c)[2]
    rx = S2.reference_3d_extrap(c)
    assert abs(rx / rp - 1.0) < 0.01
    assert abs(S2.reference_3d(c, px_div=6) / rp - 1.0) > abs(rx / rp - 1.0)


def test_flux_condition_mean_temperature_is_linear_in_a_homogeneous_cell():
    """!
    @brief Review check of the flux path of the unit-cell solver against an exact identity: in a homogeneous cell (every conductivity equal) with an adiabatic wall the mean temperature of a
           horizontal section is exactly linear in z between the sources, whatever the flux pattern on the top (it is applied on the solid only, not over the hole, so the field is not
           one-dimensional). The node-to-node resistance between the mid-planes of the two foils is then (t - t_foil) / (k A) under the flux condition too.
    @return None.
    """
    area, k, t, t_foil = math.pi * (1.25e-3) ** 2, 2.0, 1.6e-3, 35e-6
    for bc in ("isothermal", "flux"):
        r = AC.unit_cell_k(area, 0.6e-3, 0.56e-3, t, k_fr4_z=k, k_fr4_r=k, k_cu=k, k_fill=k, t_foil=t_foil, bc=bc)
        assert r["r_nodes"] == pytest.approx((t - t_foil) / (k * area), rel=1e-9)
    # the face reading under the flux condition is NOT the one-dimensional value (the flux skips the hole): the identity is a test of the mean, not a trivial 1D field
    r = AC.unit_cell_k(area, 0.6e-3, 0.56e-3, t, k_fr4_z=k, k_fr4_r=k, k_cu=k, k_fill=k, t_foil=t_foil, bc="flux")
    assert abs(r["k_eff"] / k - 1.0) > 1e-3


def test_extrapolation_recovers_the_limit_of_a_synthetic_error_model(monkeypatch):
    """!
    @brief Review check of `reference_3d_extrap` without any solve: with a synthetic reference R(px, n) = R0 + b / px + c / px^2 + d / n^2 (the error model the extrapolation assumes) it returns
           R0 to rounding; with a first-order pixel error of non-integer order (px^-1.65, the order observed between S/8, S/16 and S/32 in README 11.1) it is off by a measured, small amount,
           which is the size of the extrapolation uncertainty quoted in README 16.2.
    @return None.
    """
    c = {"S": 2.0, "W": 20.0, "t": 1.6, "kxy": 0.9, "kz": 0.3, "h": 1.0e6}
    monkeypatch.setattr(S2, "reference_3d", lambda c_, pad=False, px=16, ns=16: 380.0 + 60.0 / px + 90.0 / px ** 2 + 2000.0 / ns ** 2)
    assert S2.reference_3d_extrap(c) == pytest.approx(380.0, rel=1e-12)
    monkeypatch.setattr(S2, "reference_3d", lambda c_, pad=False, px=16, ns=16: 380.0 + 300.0 / px ** 1.65 + 2000.0 / ns ** 2)
    assert abs(S2.reference_3d_extrap(c) / 380.0 - 1.0) < 0.005
