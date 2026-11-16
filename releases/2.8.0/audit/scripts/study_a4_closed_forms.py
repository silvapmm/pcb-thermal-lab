#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_a4_closed_forms.py
@brief Audit L11: the Lumped closed forms against independent numerical solutions (nothing of the program but the functions under test):
       (1) the Bessel factors f_R, f_P of a uniformly heated disc on a leaking sheet against a radial finite-volume solve; (2) the self distance 0.447 of a square
       (geometric mean distance) by quadrature; (3) annulus_out_resistance, rim_minus_mean and krogh against radial finite volumes.
@details Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_a4_closed_forms.py $PWD (releases/2.8.0/audit/REVIEW_A4.md).
"""
import sys, math, numpy as np
sys.path.insert(0, sys.argv[1])
from pcbthermal.lumped import _interior_factors
from pcbthermal.viaconstriction import annulus_out_resistance, rim_minus_mean, krogh

def radial(r0, r1, n, S, g, q_of_r, inner_flux0=True, outer_T=None, outer_insulated=False, sink_T_at_r0=None):
    """!
    @brief Cell-centred radial finite volumes on [r0, r1] for -S (1/r)(r T')' + g T = q(r).
    @param r0 Inner radius in m.
    @param r1 Outer radius in m.
    @param n Number of rings.
    @param S Sheet conductance in W/K.
    @param g Loss per area in W/m2K.
    @param q_of_r Source per area in W/m2 as a function of r.
    @param inner_flux0 Insulated inner side (always; kept for clarity).
    @param outer_T Fixed temperature at r1, or None.
    @param outer_insulated Insulated outer side (the default when outer_T is None).
    @param sink_T_at_r0 Fixed temperature at r0, or None.
    @return Tuple (centres, ring areas, temperatures).
    """
    e = np.linspace(r0, r1, n + 1); c = 0.5 * (e[1:] + e[:-1]); A = np.zeros((n, n)); b = np.zeros(n)
    area = math.pi * (e[1:] ** 2 - e[:-1] ** 2)
    for i in range(n):
        A[i, i] += g * area[i]; b[i] += q_of_r(c[i]) * area[i]
        if i + 1 < n:
            G = S * 2 * math.pi * e[i + 1] / (c[i + 1] - c[i]); A[i, i] += G; A[i + 1, i + 1] += G; A[i, i + 1] -= G; A[i + 1, i] -= G
    if outer_T is not None:
        G = S * 2 * math.pi * e[-1] / (e[-1] - c[-1]); A[-1, -1] += G; b[-1] += G * outer_T
    if sink_T_at_r0 is not None:
        G = S * 2 * math.pi * e[0] / (c[0] - e[0]); A[0, 0] += G; b[0] += G * sink_T_at_r0
    return c, area, np.linalg.solve(A, b)

S = 0.0135   # W/K (35 um copper)
print("(1) disc factors: x, fR code, fR numeric, fP code, fP numeric")
for x in (0.05, 0.3, 1.0, 2.0, 4.0, 8.0):
    a = 2e-3; lam = a / x; g = S / lam ** 2; q = 1e4
    # outer boundary: disc edge held at T_b chosen so that the disc is the interior problem: solve on the disc with the exact boundary value of theta(a)
    # theta(r) = q/g + A0 I0(r/lam); pick A0 = -1 (any value: the factors are ratios) -> theta(a) known; FV with Dirichlet at r = a
    from scipy.special import iv
    A0 = -q / g / iv(0, x) * 0.5
    Ta = q / g + A0 * iv(0, x)
    c, area, T = radial(0.0, a, 4000, S, g, lambda r: q, outer_T=Ta)
    mean = (T * area).sum() / area.sum()
    # lateral outflow = generation - vertical loss
    Qlat = q * area.sum() - g * (T * area).sum()
    T0 = T[0]
    fr_n = 4 * (mean - Ta) * 2 * math.pi * S / Qlat; fp_n = 4 * (T0 - mean) * 2 * math.pi * S / Qlat
    fr, fp = _interior_factors(x)
    print(f"  {x:5.2f} {float(fr):.5f} {fr_n:.5f} {float(fp):.5f} {fp_n:.5f}")
print("(2) geometric mean distance of a unit square to itself")
rng = np.random.default_rng(1); n = 4_000_000
p = rng.random((n, 2)); qq = rng.random((n, 2)); d = np.hypot(*(p - qq).T)
print(f"  Monte Carlo exp(mean ln d) = {math.exp(np.log(d).mean()):.5f} (code 0.447); closed form exp(-25/12 + pi/3 + 2/3 ln 2... ) see note")
# exact: ln GMD = ln(a) + (1/3) ln 2 + pi/3 - 25/12 (Maxwell)
print(f"  Maxwell closed form: {math.exp(math.log(2)/3 + math.pi/3 - 25/12):.5f}")
print("(3) annulus_out_resistance: rin, rout, code, numeric")
for rin, rout in ((0.2e-3, 2e-3), (1e-3, 2e-3), (1.9e-3, 2e-3)):
    q = 1.0
    c, area, T = radial(rin, rout, 4000, S, 0.0, lambda r: q, outer_T=0.0)
    num = (T * area).sum() / area.sum() / (q * area.sum())
    print(f"  {rin*1e3:.2f} {rout*1e3:.2f} {annulus_out_resistance(S, rin, rout):.6f} {num:.6f}")
print("(4) Krogh cell (uniform source over cell, sink wall at a, insulated outer rim R): krogh mean-to-wall and rim-minus-mean, code vs numeric")
for a, R in ((0.15e-3, 0.6e-3), (0.15e-3, 2e-3)):
    q = 1.0
    c, area, T = radial(a, R, 6000, S, 0.0, lambda r: q, sink_T_at_r0=0.0)
    W = q * area.sum(); mean = (T * area).sum() / area.sum()
    rim = T[-1] + (T[-1] - T[-2]) * 0.5  # extrapolate to the rim (flux zero: slope ~0)
    print(f"  a {a*1e3:.2f} R {R*1e3:.2f} | krogh {krogh(S, R, a):.6f} num {mean/W:.6f} | rim-mean {rim_minus_mean(S, R, a):.6f} num {(T[-1]-mean)/W:.6f}")
